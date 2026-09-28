from datetime import datetime
from typing import Any, Optional, Protocol

from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService
from src.business.algortimos.sismos.SismoValidationService import (
    SismoValidationError,
    SismoValidationService,
)
from src.Models.Sismo import Sismo, StatusSismo
from src.business.services.AvlService import AvlService
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

    def _validar_timestamp_contra_reloj(self, timestamp) -> None:
        """Raises SismoValidationError if the timestamp is later than the
        simulation clock (section 3)."""
        if self.reloj_service is not None and self.reloj_service.es_posterior_al_reloj(timestamp):
            raise SismoValidationError(
                f"El timestamp del evento ({timestamp}) no puede ser posterior "
                f"al reloj de simulación ({self.reloj_service.obtener_reloj()})."
            )

    def _derivar_prioridad_y_clave(self, sismo_id: int, magnitude: float, depth: float,
                                   epicenter_x: float, epicenter_y: float):
        """Priority is ALWAYS derived from current data (section 4), never
        taken from the caller. Returns (None, None) if there is no
        zone service configured."""
        if self.zona_service is None:
            return None, None
        zona_poblada = self.zona_service.punto_en_zona(longitud=epicenter_x, latitud=epicenter_y)
        prioridad = PriorityKeyService.calcular_prioridad(magnitude, depth, zona_poblada)
        return prioridad, PriorityKeyService.generar_clave(prioridad, magnitude, sismo_id)

    def _validar_datos_fisicos(self, magnitude, depth, epicenter_x, epicenter_y, timestamp):
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
        return self.eliminados_service is not None and self.eliminados_service.esta_retirado(sismo_id)

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
            raise SismoValidationError("El identificador de la estación no puede estar vacío.")

        sismo = self.get_by_id(sismo_id)
        sismo.reporting_stations.add(station)
        if sismo.clave is None:
            sismo.prioridad, sismo.clave = self._derivar_prioridad_y_clave(
                sismo.id, sismo.magnitude, sismo.depth, sismo.epicenter_x, sismo.epicenter_y
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
            raise SismoValidationError("La revisión es obligatoria al aplicar una corrección.")
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
        sismo.prioridad, sismo.clave = self._derivar_prioridad_y_clave(sismo.id, mag, depth_v, x, y)
        sismo.reporting_stations.add(station)
        sismo.revision = revision
        sismo.status = StatusSismo.PENDIENTE

        return self._guardar_y_sincronizar(sismo)

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
        """Individual deletion: removes only this event from the AVL (its
        descendants stay active) and registers the id as retired."""
        val_id = SismoValidationService.validate_id(sismo_id)
        self.get_by_id(val_id)

        eliminado = self.repository.delete(val_id)
        if eliminado and self.avl_service is not None:
            self.avl_service.eliminar_evento(val_id)
        if eliminado and self.eliminados_service is not None:
            self.eliminados_service.marcar_retirado(val_id)
        return eliminado

    delete_event = delete

    def update_event(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
    ) -> Sismo:
        """Manual correction (section 6): if the current revision is r it
        ALWAYS produces r + 1, even when the new key equals the old one.
        All data is validated before applying any change; the event goes
        back to pending and the AVL relocates it if P or M changed."""
        sismo = self.get_by_id(sismo_id)
        mag, depth_v, x, y, ts = self._validar_datos_fisicos(
            magnitude, depth, epicenter_x, epicenter_y, timestamp
        )

        sismo.magnitude, sismo.depth = mag, depth_v
        sismo.epicenter_x, sismo.epicenter_y, sismo.timestamp = x, y, ts
        sismo.prioridad, sismo.clave = self._derivar_prioridad_y_clave(sismo.id, mag, depth_v, x, y)
        sismo.revision += 1
        sismo.status = StatusSismo.PENDIENTE

        return self._guardar_y_sincronizar(sismo)

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