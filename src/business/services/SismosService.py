from dataclasses import replace
from datetime import datetime
from typing import Any, Optional, Protocol

from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService
from src.business.algortimos.sismos.SismoComparison import SismoComparison
from src.business.algortimos.sismos.SismoValidationService import (
    SismoValidationError,
    SismoValidationService,
)
from src.Models.Sismo import EstadoPersistencia, Sismo, StatusSismo
from src.dataaccess.repository.HistorialSismosRepository import (
    HistorialSismosRepository,
)
from src.business.services.AvlService import AvlService
from src.business.services.ConfiguracionEscenarioService import (
    ConfiguracionEscenarioService,
)
from src.business.services.EliminadosService import EliminadosService
from src.business.services.RelojService import RelojService
from src.business.services.ZonaService import ZonaService


class SismoNotFoundError(KeyError):
    """Excepción lanzada cuando no se encuentra un evento sísmico en el sistema."""

    pass


class ISismoRepository(Protocol):
    """Interfaz (Protocolo) para abstraer la capa de persistencia de sismos."""

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """Obtiene un sismo por su ID único."""
        ...

    def get_all(self) -> list[Sismo]:
        """Recupera la lista completa de sismos."""
        ...

    def save(self, sismo: Sismo) -> Sismo:
        """Guarda o actualiza un sismo en el almacén de datos."""
        ...

    def delete(self, sismo_id: int) -> bool:
        """Elimina un sismo según su ID."""
        ...

    def generate_next_id(self) -> int:
        """Genera el siguiente identificador numérico disponible."""
        ...


class SismoService:
    """Capa de servicio para la gestión de entidades Sismo.

    Implementa la lógica de negocio relativa a la creación, actualización,
    consenso entre estaciones, control de revisiones, priorización y auditoría.
    """

    def __init__(
        self,
        repository: ISismoRepository,
        avl_service: Optional[AvlService] = None,
        zona_service: Optional[ZonaService] = None,
        reloj_service: Optional[RelojService] = None,
        eliminados_service: Optional[EliminadosService] = None,
        historial_repository: Optional[HistorialSismosRepository] = None,
        configuracion_service: Optional[ConfiguracionEscenarioService] = None,
        acciones_service: object | None = None,
    ):
        """Inicializa el servicio con su repositorio de persistencia.

        Args:
            repository (ISismoRepository): Instancia del repositorio de sismos.
            avl_service (Optional[AvlService]): Servicio que sincroniza
                el catálogo activo con el árbol AVL. Si se omite, el sismo se
                guarda igual, pero no se refleja en el árbol.
            zona_service (Optional[ZonaService]): Servicio para determinar si
                el epicentro cae en zona poblada. Necesario para calcular la
                prioridad de inmediato al crear un evento (sección 6 del
                enunciado). Si se omite, create_event deja prioridad/clave
                en None, igual que antes.
            reloj_service (Optional[RelojService]): Reloj de simulación del
                escenario. Si se provee, valida que ningún evento tenga un
                timestamp posterior al reloj (sección 3 del enunciado). Si
                se omite, no se aplica esa validación.
            eliminados_service (Optional[EliminadosService]): Registro de
                ids retirados. Si se provee, bloquea la creación con un id
                ya eliminado, y marca como retirado cada id que se elimine.
        """
        self.repository = repository
        self.avl_service = avl_service
        self.zona_service = zona_service
        self.reloj_service = reloj_service
        self.eliminados_service = eliminados_service
        self.historial_repository = historial_repository
        self.configuracion_service = configuracion_service
        # Kept only for constructor compatibility; undo is centralized in
        # HistorialService and this legacy service is never invoked.
        self._legacy_actions_service = acciones_service
        # Accumulated metrics of this service (section 14). They will be
        # part of the restorable state when undo/versions are added.
        self.contadores = {
            "correcciones_aceptadas": 0,
            "reportes_descartados": 0,
            "conflictos": 0,
            "archivos_masivos": 0,
            "eventos_archivados": 0,
        }

    # Queue decision -> section 14 counter it increments
    _CONTADOR_POR_DECISION = {
        "conflicto": "conflictos",
        "reporte_antiguo": "reportes_descartados",
        "identificador_retirado": "reportes_descartados",
        "datos_invalidos": "reportes_descartados",
        "ruido": "reportes_descartados",
    }

    def sumar_contador(self, nombre: str, cantidad: int = 1) -> None:
        """Adds to a section 14 counter. .get() keeps older snapshots,
        exports and versions (without the newer keys) working."""
        self.contadores[nombre] = self.contadores.get(nombre, 0) + cantidad

    def registrar_rechazo(self, decision: str) -> None:
        """Counts a queue report that was rejected or discarded."""
        nombre = self._CONTADOR_POR_DECISION.get(decision)
        if nombre is not None:
            self.sumar_contador(nombre)

    def _validar_timestamp_contra_reloj(self, timestamp) -> None:
        """Raises SismoValidationError if the timestamp is later than the
        simulation clock (section 3)."""
        if self.reloj_service is not None and self.reloj_service.es_posterior_al_reloj(
            timestamp
        ):
            raise SismoValidationError(
                f"El timestamp del evento ({timestamp}) no puede ser posterior "
                f"al reloj de simulación ({self.reloj_service.obtener_reloj()})."
            )

    def _derivar_prioridad_y_clave(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
    ):
        """Priority is ALWAYS derived from current data (section 4), never
        taken from the caller. Returns (None, None) if there is no
        zone service configured."""
        if self.zona_service is None:
            return None, None
        zona_poblada = self.zona_service.punto_en_zona(
            longitud=epicenter_x, latitud=epicenter_y
        )
        prioridad = PriorityKeyService.calcular_prioridad(
            magnitude, depth, zona_poblada
        )
        return prioridad, PriorityKeyService.generar_clave(
            prioridad, magnitude, sismo_id
        )

    def _validar_datos_fisicos(
        self, magnitude, depth, epicenter_x, epicenter_y, timestamp
    ):
        """Validates EVERYTHING before touching any structure, so an invalid
        field never produces a partial update (section 6)."""
        datos = (
            SismoValidationService.validate_magnitude(magnitude),
            SismoValidationService.validate_depth(depth),
            SismoValidationService.validate_epicenter_coord(epicenter_x, "epicenter_x"),
            SismoValidationService.validate_epicenter_coord(epicenter_y, "epicenter_y"),
            SismoValidationService.validate_timestamp(timestamp),
        )
        self._validar_timestamp_contra_reloj(datos[4])
        return datos

    def _esta_retirado(self, sismo_id: int) -> bool:
        return (
            self.eliminados_service is not None
            and self.eliminados_service.esta_retirado(sismo_id)
        )

    def _guardar_y_sincronizar(self, sismo: Sismo) -> Sismo:
        sismo_guardado = self.repository.save(sismo)
        if self.avl_service is not None:
            self.avl_service.sincronizar_desde_sismo(sismo_guardado)
        return sismo_guardado

    # ------------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------------

    def create_event(
        self,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
        initial_station_id: Optional[str] = None,
        sismo_id: Optional[int] = None,
        revision: int = 1,
    ) -> Sismo:
        """Creates an event as a single action (section 6): validates, assigns
        the revision, derives priority and key K=(P,M,I), inserts it in the
        AVL and leaves it pending.

        sismo_id is entered by the user of each station (section 3). If it is
        omitted a free id is generated. An id that is active or retired
        (deleted) is rejected. `revision` lets a report with an unknown id
        start directly at a revision greater than 1.
        """
        station = SismoValidationService.validate_station_id(initial_station_id)

        if sismo_id is None:
            sismo_id = self.repository.generate_next_id()
            while self._esta_retirado(sismo_id):
                sismo_id += 1
        sismo_id = SismoValidationService.validate_id(sismo_id)

        if self._esta_retirado(sismo_id):
            raise SismoValidationError(
                f"El identificador {sismo_id} fue eliminado y está retirado: "
                f"no puede reutilizarse ni reactivarse."
            )
        if self.repository.get_by_id(sismo_id) is not None:
            raise SismoValidationError(
                f"Ya existe un evento con el identificador {sismo_id}."
            )
        if not isinstance(revision, int) or revision < 1:
            raise SismoValidationError("La revisión debe ser un entero positivo.")

        mag, depth_v, x, y, ts = self._validar_datos_fisicos(
            magnitude, depth, epicenter_x, epicenter_y, timestamp
        )
        prioridad, clave = self._derivar_prioridad_y_clave(sismo_id, mag, depth_v, x, y)

        sismo = Sismo(
            id=sismo_id,
            magnitude=mag,
            depth=depth_v,
            epicenter_x=x,
            epicenter_y=y,
            timestamp=ts,
            revision=revision,
            reporting_stations={station} if station else set(),
            prioridad=prioridad,
            clave=clave,
            status=StatusSismo.PENDIENTE,
            estado_persistencia=EstadoPersistencia.ACTIVO,
        )
        return self._guardar_y_sincronizar(sismo)

    # ------------------------------------------------------------------
    # CONFIRMATION AND CORRECTION (reports)
    # ------------------------------------------------------------------

    def add_consensus_report(
        self,
        sismo_id: int,
        station_id: str,
        prioridad: Optional[int] = None,
        clave: Optional[tuple[int, float, int]] = None,
    ) -> Sismo:
        """Confirmation: adds the station (a set, so repeating the same
        confirmation never duplicates it). Revision and data unchanged.
        `prioridad`/`clave` are kept for backwards compatibility and ignored:
        the key is always derived from current data."""
        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío."
            )

        sismo = self.get_by_id(sismo_id)
        sismo.reporting_stations.add(station)
        if sismo.clave is None:
            sismo.prioridad, sismo.clave = self._derivar_prioridad_y_clave(
                sismo.id,
                sismo.magnitude,
                sismo.depth,
                sismo.epicenter_x,
                sismo.epicenter_y,
            )
        return self._guardar_y_sincronizar(sismo)

    def apply_correction(
        self,
        sismo_id: int,
        station_id: str,
        magnitude: Optional[float] = None,
        depth: Optional[float] = None,
        epicenter_x: Optional[float] = None,
        epicenter_y: Optional[float] = None,
        prioridad: Optional[int] = None,
        clave: Optional[tuple[int, float, int]] = None,
        revision: Optional[int] = None,
        timestamp: Optional[datetime | str] = None,
    ) -> Sismo:
        """Correction coming from a report with a greater revision.

        Everything is validated first; then the data is replaced, the
        priority/key recomputed (the AVL removes with the old key and
        reinserts with the new one if P or M changed) and the event goes
        back to pending. Fields not sent keep their current value.
        """
        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío al aplicar corrección."
            )

        sismo = self.get_by_id(sismo_id)

        if revision is None:
            raise SismoValidationError(
                "La revisión es obligatoria al aplicar una corrección."
            )
        if not isinstance(revision, int):
            raise SismoValidationError("La revisión debe ser un número entero.")
        if revision <= sismo.revision:
            raise SismoValidationError(
                f"La revisión recibida ({revision}) debe ser mayor "
                f"que la revisión actual del sismo ({sismo.revision})."
            )

        mag, depth_v, x, y, ts = self._validar_datos_fisicos(
            sismo.magnitude if magnitude is None else magnitude,
            sismo.depth if depth is None else depth,
            sismo.epicenter_x if epicenter_x is None else epicenter_x,
            sismo.epicenter_y if epicenter_y is None else epicenter_y,
            sismo.timestamp if timestamp is None else timestamp,
        )

        sismo.magnitude, sismo.depth = mag, depth_v
        sismo.epicenter_x, sismo.epicenter_y, sismo.timestamp = x, y, ts
        sismo.prioridad, sismo.clave = self._derivar_prioridad_y_clave(
            sismo.id, mag, depth_v, x, y
        )
        sismo.reporting_stations.add(station)
        sismo.revision = revision
        sismo.status = StatusSismo.PENDIENTE

        guardado = self._guardar_y_sincronizar(sismo)
        self.contadores["correcciones_aceptadas"] += 1
        return guardado

    # ------------------------------------------------------------------
    # ATTENTION STATUS
    # ------------------------------------------------------------------

    def audit_and_validate(self, sismo_id: int) -> Sismo:
        """Marks the event as reviewed. P, M and I do not change, so the
        key is the same and the node is NOT reinserted (section 6)."""
        sismo = self.get_by_id(sismo_id)
        sismo.status = StatusSismo.REVISADO
        return self._guardar_y_sincronizar(sismo)

    # ------------------------------------------------------------------
    # DELETION AND MANUAL CORRECTION
    # ------------------------------------------------------------------

    def delete(self, sismo_id: Any) -> bool:
        """Deletes one event and records it as one undoable action."""
        val_id = SismoValidationService.validate_id(sismo_id)
        anterior = self.get_by_id(val_id)
        ids_retirados_antes = (
            self.eliminados_service.todos()
            if self.eliminados_service is not None
            else set()
        )
        retirado = replace(
            anterior,
            estado_persistencia=EstadoPersistencia.RETIRADO,
            reporting_stations=set(anterior.reporting_stations),
        )
        try:
            eliminado = self.repository.delete(val_id)
            if not eliminado:
                return False
            if self.historial_repository is not None:
                self.historial_repository.save(retirado)
            if self.avl_service is not None and not self.avl_service.eliminar_evento(
                val_id
            ):
                raise RuntimeError("No se pudo retirar el evento del AVL.")
            if self.eliminados_service is not None:
                self.eliminados_service.marcar_retirado(val_id)
        except Exception:
            if self.historial_repository is not None:
                self.historial_repository.delete(val_id)
            self._restaurar_eventos([anterior], ids_retirados_antes)
            raise

        return True

    def archivar_rama(self, sismo_id: Any) -> dict:
        """Archives the frozen AVL subtree rooted at ``sismo_id``."""
        val_id = SismoValidationService.validate_id(sismo_id)
        ids = self.avl_service.capturar_subarbol(val_id) if self.avl_service else []
        if not ids:
            self.get_by_id(val_id)
            ids = [val_id]

        eventos = [self.get_by_id(identificador) for identificador in ids]
        ids_retirados_antes = (
            self.eliminados_service.todos()
            if self.eliminados_service is not None
            else set()
        )
        archivados = [
            replace(
                evento,
                estado_persistencia=EstadoPersistencia.ARCHIVADO,
                reporting_stations=set(evento.reporting_stations),
            )
            for evento in eventos
        ]
        try:
            for evento in eventos:
                if not self.repository.delete(evento.id):
                    raise RuntimeError(f"No se pudo retirar el evento {evento.id}.")
            if self.historial_repository is not None:
                for evento in archivados:
                    self.historial_repository.save(evento)
            if self.avl_service is not None:
                resultado_avl = self.avl_service.eliminar_subarbol(val_id)
                if sorted(resultado_avl["ids_eliminados"]) != sorted(ids):
                    raise RuntimeError(
                        "El AVL no retiró exactamente la rama capturada."
                    )
            else:
                resultado_avl = {
                    "ids_capturados": ids,
                    "ids_eliminados": ids,
                    "cantidad": len(ids),
                }
        except Exception:
            self._restaurar_eventos(eventos, ids_retirados_antes)
            for evento in archivados:
                if self.historial_repository is not None:
                    self.historial_repository.delete(evento.id)
            raise

        # Section 14 counters: one mass archive and n archived events
        self.sumar_contador("archivos_masivos")
        self.sumar_contador("eventos_archivados", len(ids))
        return {
            "accion": "archivo_rama",
            "raiz": val_id,
            "eventos_archivados": ids,
            "cantidad": len(ids),
            "avl": resultado_avl,
        }

    def ramas_elegibles_para_archivo(self) -> list[dict]:
        """Returns a frozen evaluation of every eligible active subtree."""
        if self.avl_service is None or self.reloj_service is None:
            return []

        limite_antiguedad = (
            self.configuracion_service.antiguedad_archivo_horas
            if self.configuracion_service is not None
            else 72.0
        )
        arbol = self.avl_service.get_arbol()
        candidatos = []
        for nodo in arbol.inorden():
            raiz_id = nodo.getClave()[2]
            ids = self.avl_service.capturar_subarbol(raiz_id)
            eventos = [self.get_by_id(identificador) for identificador in ids]
            antiguedades = [
                self.reloj_service.antiguedad_en_horas(evento.timestamp)
                for evento in eventos
            ]
            prioridad_baja = all(evento.clave is not None and evento.clave[0] == 1 for evento in eventos)
            antiguedad_suficiente = all(
                antiguedad > limite_antiguedad for antiguedad in antiguedades
            )
            if prioridad_baja and antiguedad_suficiente:
                candidatos.append({
                    "raiz": raiz_id,
                    "ids": ids,
                    "cantidad": len(ids),
                    "profundidad_raiz": arbol.profundidadDe(nodo),
                    "prioridad_baja": True,
                    "antiguedad_minima_horas": min(antiguedades),
                    "T": limite_antiguedad,
                })
        return sorted(
            candidatos,
            key=lambda candidato: (
                -candidato["cantidad"],
                -candidato["profundidad_raiz"],
                -candidato["raiz"],
            ),
        )

    def previsualizar_archivo_rama_elegible(self) -> dict:
        candidatos = self.ramas_elegibles_para_archivo()
        if not candidatos:
            return {
                "elegible": False,
                "raiz": None,
                "ids": [],
                "cantidad": 0,
                "candidatos": [],
                "mensaje": "No existe una rama elegible para archivo.",
            }
        seleccion = candidatos[0]
        resultado = dict(seleccion)
        resultado["elegible"] = True
        resultado["candidatos"] = candidatos
        resultado["justificacion"] = (
            "Mayor cantidad de nodos entre las ramas elegibles; "
            "los empates se resolvieron por profundidad y luego por identificador."
        )
        return resultado

    def archivar_rama_elegible(self) -> dict:
        seleccion = self.previsualizar_archivo_rama_elegible()
        if not seleccion["elegible"]:
            return seleccion
        resultado = self.archivar_rama(seleccion["raiz"])
        resultado.update({
            "seleccion": seleccion,
            "justificacion": seleccion["justificacion"],
        })
        return resultado

    def _restaurar_eventos(self, eventos: list[Sismo], ids_retirados: set[int]) -> None:
        for evento in eventos:
            self.repository.save(
                replace(
                    evento,
                    estado_persistencia=EstadoPersistencia.ACTIVO,
                    reporting_stations=set(evento.reporting_stations),
                )
            )
            if self.avl_service is not None:
                self.avl_service.sincronizar_desde_sismo(evento)
        if self.eliminados_service is not None:
            self.eliminados_service.cargar_ids(ids_retirados)

    def get_historico(self) -> list[Sismo]:
        """Devuelve los eventos que ya no pertenecen al catálogo activo."""
        if self.historial_repository is None:
            return []
        return self.historial_repository.get_all()

    def get_historico_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """Consulta un evento archivado o retirado por su identificador."""
        if self.historial_repository is None:
            return None
        return self.historial_repository.get_by_id(sismo_id)

    def confirmar_evento_archivado(self, sismo_id: int, station_id: str) -> Sismo:
        """Adds a station to an archived event without reactivating it."""
        if self.historial_repository is None:
            raise SismoNotFoundError(f"No existe histórico para el evento {sismo_id}.")
        archivado = self.historial_repository.get_by_id(sismo_id)
        if (
            archivado is None
            or archivado.estado_persistencia != EstadoPersistencia.ARCHIVADO
        ):
            raise SismoNotFoundError(
                f"No existe un evento archivado con ID {sismo_id}."
            )
        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de estación no puede estar vacío."
            )
        archivado.reporting_stations.add(station)
        self.historial_repository.save(archivado)
        return archivado

    def reactivar_evento_archivado(
        self,
        sismo_id: int,
        station_id: str,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
        revision: int,
    ) -> Sismo:
        """Reactivates an archived event using a strictly newer revision."""
        if self.historial_repository is None:
            raise SismoNotFoundError(f"No existe histórico para el evento {sismo_id}.")
        anterior = self.historial_repository.get_by_id(sismo_id)
        if (
            anterior is None
            or anterior.estado_persistencia != EstadoPersistencia.ARCHIVADO
        ):
            raise SismoNotFoundError(
                f"No existe un evento archivado con ID {sismo_id}."
            )

        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de estación no puede estar vacío."
            )
        if not isinstance(revision, int) or revision <= anterior.revision:
            raise SismoValidationError(
                f"La revisión recibida ({revision}) debe ser mayor "
                f"que la revisión archivada ({anterior.revision})."
            )
        mag, depth_v, x, y, ts = self._validar_datos_fisicos(
            magnitude, depth, epicenter_x, epicenter_y, timestamp
        )
        prioridad, clave = self._derivar_prioridad_y_clave(sismo_id, mag, depth_v, x, y)
        nuevo = replace(
            anterior,
            magnitude=mag,
            depth=depth_v,
            epicenter_x=x,
            epicenter_y=y,
            timestamp=ts,
            revision=revision,
            prioridad=prioridad,
            clave=clave,
            reporting_stations=set(anterior.reporting_stations) | {station},
            status=StatusSismo.PENDIENTE,
            estado_persistencia=EstadoPersistencia.ACTIVO,
        )
        try:
            self.historial_repository.delete(sismo_id)
            self.repository.save(nuevo)
            if self.avl_service is not None:
                self.avl_service.sincronizar_desde_sismo(nuevo)
        except Exception:
            self.repository.delete(sismo_id)
            self.historial_repository.save(anterior)
            raise
        return nuevo

    delete_event = delete

    # ------------------------------------------------------------------
    # MANUAL CORRECTION (section 6) -- one single, all-or-nothing action
    # ------------------------------------------------------------------

    CAMPOS_CORREGIBLES = (
        "magnitude",
        "depth",
        "epicenter_x",
        "epicenter_y",
        "timestamp",
    )

    def corregir_evento(self, sismo_id: int, cambios: dict) -> dict:
        """
        Manual correction of an ACTIVE event.

        `cambios` may contain one or several of CAMPOS_CORREGIBLES; the
        fields not sent keep their current value. The identifier is
        immutable: an "id" different from `sismo_id` is rejected.

        Steps (all or nothing):
          1. Keep the previous state (a copy) and validate ALL resulting
             data before touching anything.
          2. Recompute populated-zone membership, priority and key.
          3. Revision r -> r + 1 ALWAYS (even if the key does not change)
             and status back to pending.
          4. AVL: remove with the old key and reinsert with the new one;
             if the key is the same the node is kept in place and the order
             is proven against its in-order neighbors.
          5. Persist. If anything fails, the tree and the counters are
             restored to the previous state and the error is raised.
          6. Update metrics (accepted corrections).

        Returns {"sismo", "anterior", "reporte"} so the UI can explain
        what happened and why.
        """
        if not isinstance(cambios, dict) or not cambios:
            raise SismoValidationError(
                "La corrección debe incluir al menos un dato a modificar."
            )

        val_id = SismoValidationService.validate_id(sismo_id)
        if "id" in cambios and cambios["id"] not in (None, ""):
            try:
                id_recibido = int(cambios["id"])
            except (TypeError, ValueError):
                id_recibido = None
            if id_recibido != val_id:
                raise SismoValidationError(
                    "El identificador es inmutable: no puede cambiarse en una corrección."
                )

        campos = {
            k: cambios[k]
            for k in self.CAMPOS_CORREGIBLES
            if k in cambios and cambios[k] is not None
        }
        if not campos:
            raise SismoValidationError(
                "La corrección debe incluir al menos uno de: "
                + ", ".join(self.CAMPOS_CORREGIBLES)
                + "."
            )

        # 1. previous state (the repository returns an independent copy)
        anterior = self.get_by_id(val_id)

        # 1. validate everything first -- nothing is modified if this fails
        mag, depth_v, x, y, ts = self._validar_datos_fisicos(
            campos.get("magnitude", anterior.magnitude),
            campos.get("depth", anterior.depth),
            campos.get("epicenter_x", anterior.epicenter_x),
            campos.get("epicenter_y", anterior.epicenter_y),
            campos.get("timestamp", anterior.timestamp),
        )

        # 2. zone, priority and key derived from the resulting data
        zona_poblada = None
        if self.zona_service is not None:
            zona_poblada = self.zona_service.punto_en_zona(longitud=x, latitud=y)
        prioridad, clave = self._derivar_prioridad_y_clave(val_id, mag, depth_v, x, y)

        # 3. new version of the event (a new object; `anterior` stays intact)
        nuevo = replace(
            anterior,
            magnitude=mag,
            depth=depth_v,
            epicenter_x=x,
            epicenter_y=y,
            timestamp=ts,
            prioridad=prioridad,
            clave=clave,
            revision=anterior.revision + 1,
            status=StatusSismo.PENDIENTE,
            reporting_stations=set(anterior.reporting_stations),
        )

        # 4 + 5. tree and persistence as one action, with rollback
        contadores_avl = (
            self.avl_service.contadores() if self.avl_service is not None else None
        )
        reporte_arbol = None
        try:
            if self.avl_service is not None:
                reporte_arbol = self.avl_service.aplicar_correccion(anterior, nuevo)
                if not reporte_arbol["verificacion_orden"]["valido"]:
                    raise SismoValidationError(
                        "La corrección dejaría el árbol fuera de orden; se revirtió."
                    )
            self.repository.save(nuevo)
        except Exception:
            if self.avl_service is not None:
                self.avl_service.restaurar_evento(anterior, contadores_avl)
            raise

        # 6. metrics
        self.contadores["correcciones_aceptadas"] += 1

        return {
            "sismo": nuevo,
            "anterior": anterior,
            "reporte": self._reporte_correccion(
                anterior, nuevo, zona_poblada, reporte_arbol
            ),
        }

    def _reporte_correccion(
        self, anterior: Sismo, nuevo: Sismo, zona_poblada, reporte_arbol
    ) -> dict:
        """Human-readable explanation of a correction for the UI."""
        modificados = []
        if SismoComparison.decimas(anterior.magnitude) != SismoComparison.decimas(
            nuevo.magnitude
        ):
            modificados.append("magnitude")
        if SismoComparison.decimas(anterior.depth) != SismoComparison.decimas(
            nuevo.depth
        ):
            modificados.append("depth")
        if SismoComparison.millonesimas(
            anterior.epicenter_x
        ) != SismoComparison.millonesimas(nuevo.epicenter_x):
            modificados.append("epicenter_x")
        if SismoComparison.millonesimas(
            anterior.epicenter_y
        ) != SismoComparison.millonesimas(nuevo.epicenter_y):
            modificados.append("epicenter_y")
        if SismoComparison.normalizar_fecha(
            anterior.timestamp
        ) != SismoComparison.normalizar_fecha(nuevo.timestamp):
            modificados.append("timestamp")

        misma_clave = anterior.clave == nuevo.clave
        if misma_clave:
            explicacion = (
                f"La clave no cambió {tuple(nuevo.clave) if nuevo.clave else ''}: el nodo se conserva en su "
                f"posición (sin eliminar ni reinsertar). Solo se actualizaron la revisión "
                f"({anterior.revision} → {nuevo.revision}) y el estado."
            )
        else:
            motivo = []
            if anterior.prioridad != nuevo.prioridad:
                motivo.append(
                    f"la prioridad pasó de {anterior.prioridad} a {nuevo.prioridad}"
                )
            if SismoComparison.decimas(anterior.magnitude) != SismoComparison.decimas(
                nuevo.magnitude
            ):
                motivo.append(
                    f"la magnitud pasó de {anterior.magnitude} a {nuevo.magnitude}"
                )
            explicacion = (
                f"La clave cambió de {tuple(anterior.clave)} a {tuple(nuevo.clave)} porque "
                + " y ".join(motivo)
                + ": el evento se retiró con la clave anterior y se reinsertó con la nueva, "
                "conservando su identificador."
            )

        return {
            "id": nuevo.id,
            "revision_anterior": anterior.revision,
            "revision_nueva": nuevo.revision,
            "campos_modificados": modificados,
            "zona_poblada": zona_poblada,
            "prioridad_anterior": anterior.prioridad,
            "prioridad_nueva": nuevo.prioridad,
            "clave_anterior": list(anterior.clave) if anterior.clave else None,
            "clave_nueva": list(nuevo.clave) if nuevo.clave else None,
            "clave_cambio": not misma_clave,
            "estado_anterior": anterior.status.value,
            "estado_nuevo": nuevo.status.value,
            "explicacion": explicacion,
            "arbol": reporte_arbol,
            # Section 7 (associations) is not implemented yet. When it is,
            # recompute here the associations of this event and of the
            # events that used it as reference.
            "asociaciones": "pendiente: la sección 7 aún no está implementada",
        }

    def update_event(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
    ) -> Sismo:
        """Backwards compatible wrapper around corregir_evento()."""
        return self.corregir_evento(
            sismo_id,
            {
                "magnitude": magnitude,
                "depth": depth,
                "epicenter_x": epicenter_x,
                "epicenter_y": epicenter_y,
                "timestamp": timestamp,
            },
        )["sismo"]

    def metricas(self) -> dict:
        return dict(self.contadores)

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def get_by_id(self, sismo_id: int) -> Sismo:
        """Obtiene un sismo validando la existencia de su ID.

        Args:
            sismo_id (int): Identificador a buscar.

        Returns:
            Sismo: La entidad encontrada.

        Raises:
            SismoNotFoundError: Si el ID no corresponde a ningún evento guardado.
        """
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(
                f"No se encontró el evento sísmico con ID {sismo_id}."
            )

        return sismo

    def get_all(self) -> list[Sismo]:
        """Recupera el listado completo de eventos sísmicos registrados.

        Returns:
            list[Sismo]: Lista de sismos almacenados.
        """
        return self.repository.get_all()

    def consultar_pendientes(self, k: int) -> dict:
        """Returns up to k pending active events in descending K order."""
        if self.avl_service is None:
            return {"eventos": [], "nodos_avl_examinados": 0}
        nodos = list(reversed(self.avl_service.get_arbol().inorden()))
        eventos = []
        examinados = 0
        for nodo in nodos:
            examinados += 1
            evento = self.repository.get_by_id(nodo.getClave()[2])
            if evento is None or evento.status != StatusSismo.PENDIENTE:
                continue
            eventos.append(evento)
            if len(eventos) == k:
                break
        return {
            "eventos": eventos,
            "nodos_avl_examinados": examinados,
            "orden": "K descendente (P, M, I)",
            "criterio": "Se recorre el AVL en orden inverso y se detiene al reunir k pendientes.",
        }

    def consultar_por_magnitud(
        self, magnitud_minima: float, magnitud_maxima: float
    ) -> dict:
        """Returns active events in an inclusive magnitude interval."""
        if self.avl_service is None:
            return {"eventos": [], "nodos_avl_examinados": 0}
        eventos = []
        nodos = self.avl_service.get_arbol().inorden()
        for nodo in nodos:
            evento = self.repository.get_by_id(nodo.getClave()[2])
            if (
                evento is not None
                and magnitud_minima <= evento.magnitude <= magnitud_maxima
            ):
                eventos.append(evento)
        return {
            "eventos": eventos,
            "nodos_avl_examinados": len(nodos),
            "intervalo": {
                "magnitud_minima": magnitud_minima,
                "magnitud_maxima": magnitud_maxima,
                "inclusivo": True,
            },
            "criterio": (
                "Se examinan los nodos activos; el intervalo cruza las particiones "
                "de prioridad de K, por lo que no se descartan ramas de forma segura."
            ),
        }

    def consultar_por_profundidad_y_fecha(
        self,
        profundidad_maxima: float,
        fecha_desde: datetime,
        fecha_hasta: datetime,
    ) -> dict:
        """Returns active events matching inclusive depth and date ranges."""
        if self.avl_service is None:
            return {"eventos": [], "nodos_avl_examinados": 0}
        eventos = []
        nodos = self.avl_service.get_arbol().inorden()
        for nodo in nodos:
            evento = self.repository.get_by_id(nodo.getClave()[2])
            if (
                evento is not None
                and evento.depth <= profundidad_maxima
                and fecha_desde <= evento.timestamp <= fecha_hasta
            ):
                eventos.append(evento)
        return {
            "eventos": eventos,
            "nodos_avl_examinados": len(nodos),
            "filtros": {
                "profundidad_maxima": profundidad_maxima,
                "fecha_desde": fecha_desde.isoformat(),
                "fecha_hasta": fecha_hasta.isoformat(),
                "inclusivos": True,
            },
            "criterio": (
                "La fecha y la profundidad no forman parte de K; se examinan "
                "todos los nodos activos para garantizar el resultado."
            ),
        }
