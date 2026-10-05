import copy
from src.Models.Sismo import EstadoPersistencia, Sismo, StatusSismo
from src.estructuras.arbol_avl import ArbolAVL
from src.estructuras.comparador_eventos import comparador_eventos


class PersistenciaEscenarioError(ValueError):
    pass


class PersistenciaEscenarioService:
    """Validates and applies the two section 12 scenario load modes."""

    TIPOS = {"inserciones", "topologia"}

    def __init__(self, estado_service, sismo_repository):
        self.estado_service = estado_service
        self.sismo_repository = sismo_repository

    def cargar(self, contenido: object, tipo: str) -> dict:
        tipo = str(tipo or "").strip().lower()
        if tipo not in self.TIPOS:
            raise PersistenciaEscenarioError(
                "El tipo de carga debe ser 'inserciones' o 'topologia'."
            )
        if not isinstance(contenido, dict):
            raise PersistenciaEscenarioError(
                "El archivo debe contener un objeto JSON."
            )
        estado_actual = self.estado_service.capturar()
        try:
            estado_nuevo = (
                self._estado_desde_inserciones(contenido)
                if tipo == "inserciones"
                else self._estado_desde_topologia(contenido)
            )
            self.estado_service.restaurar(estado_nuevo)
        except Exception:
            self.estado_service.restaurar(estado_actual)
            raise
        return {
            "tipo_carga": tipo,
            "mensaje": "Escenario cargado completamente.",
            "cantidad_eventos": len(estado_nuevo["sismos"]),
            "modo_estres": estado_nuevo["arbol"]["modoEstres"],
        }

    def exportar(self) -> dict:
        return self.estado_service.capturar()

    def _estado_desde_inserciones(self, documento: dict) -> dict:
        eventos = documento.get("eventos")
        if not isinstance(eventos, list):
            raise PersistenciaEscenarioError(
                "La carga por inserciones requiere el arreglo 'eventos'."
            )
        ids = [self._evento_id(evento) for evento in eventos]
        if len(ids) != len(set(ids)):
            raise PersistenciaEscenarioError(
                "El archivo de inserciones contiene identificadores duplicados."
            )
        entidades = [self._entidad(evento) for evento in eventos]
        arbol = ArbolAVL(comparador_eventos)
        for evento in entidades:
            if evento.estado_persistencia != EstadoPersistencia.ACTIVO:
                raise PersistenciaEscenarioError(
                    "La carga por inserciones solo admite eventos activos."
                )
            if evento.clave is None:
                raise PersistenciaEscenarioError(
                    f"El evento {evento.id} no tiene clave K."
                )
            arbol.insertar(evento.clave, {
                "status": evento.status.value,
                "revision": evento.revision,
            })
        estado = self.estado_service.capturar()
        estado["sismos"] = [self.sismo_repository._to_dict(evento) for evento in entidades]
        estado["historico"] = []
        estado["eliminados"] = []
        estado["arbol"] = {
            "nodos": arbol.exportarTopologia(),
            "modoEstres": False,
            "contadores": arbol.getContadores(),
        }
        return estado

    def _estado_desde_topologia(self, documento: dict) -> dict:
        nodos = documento.get("nodos")
        eventos = documento.get("eventos")
        es_exportacion_completa = isinstance(documento.get("arbol"), dict)
        if es_exportacion_completa:
            nodos = documento["arbol"].get("nodos")
            eventos = documento.get("sismos")
        if not isinstance(nodos, list) or not isinstance(eventos, list):
            raise PersistenciaEscenarioError(
                "La carga por topología requiere 'nodos' y 'eventos'."
            )
        self._validar_topologia(nodos)
        entidades = [self._entidad(evento) for evento in eventos]
        por_id = {evento.id: evento for evento in entidades}
        ids_nodos = [int(nodo["clave"][2]) for nodo in nodos]
        if len(ids_nodos) != len(set(ids_nodos)) or set(ids_nodos) != set(por_id):
            raise PersistenciaEscenarioError(
                "Los nodos y los eventos no tienen las mismas identidades únicas."
            )
        for nodo in nodos:
            evento = por_id[int(nodo["clave"][2])]
            clave = tuple(nodo["clave"])
            if (
                evento.clave != clave
                or evento.prioridad != clave[0]
                or float(evento.magnitude) != float(clave[1])
            ):
                raise PersistenciaEscenarioError(
                    f"Metadatos inconsistentes para el evento {evento.id}."
                )
        modo_estres = bool(
            documento.get("modoEstres", documento.get("arbol", {}).get("modoEstres", False))
        )
        temporal = ArbolAVL(comparador_eventos)
        temporal.importarTopologia(nodos, modo_estres)
        datos_por_clave = {
            tuple(item["clave"]): item for item in nodos
        }
        for nodo in temporal.inorden():
            izquierdo = nodo.getHijoIzquierdo()
            derecho = nodo.getHijoDerecho()
            altura_real = max(
                -1 if izquierdo is None else izquierdo.getAltura(),
                -1 if derecho is None else derecho.getAltura(),
            ) + 1
            factor = temporal.factorBalance(nodo)
            original = datos_por_clave[tuple(nodo.getClave())]
            if original.get("altura", 0) != altura_real:
                raise PersistenciaEscenarioError(
                    f"Altura inconsistente para la clave {list(nodo.getClave())}."
                )
            if not modo_estres and abs(factor) > 1:
                raise PersistenciaEscenarioError(
                    "Una topología desbalanceada requiere modo estrés."
                )
        estado = (
            copy.deepcopy(documento)
            if es_exportacion_completa
            else self.estado_service.capturar()
        )
        estado["sismos"] = [
            self.sismo_repository._to_dict(evento) for evento in entidades
        ]
        if not es_exportacion_completa:
            estado["historico"] = []
            estado["eliminados"] = []
        estado["arbol"] = {
            "nodos": copy.deepcopy(nodos),
            "modoEstres": modo_estres,
            "contadores": documento.get(
                "contadores", documento.get("arbol", {}).get("contadores", {})
            ),
        }
        return estado

    @staticmethod
    def _evento_id(evento: object) -> int:
        if not isinstance(evento, dict) or "id" not in evento:
            raise PersistenciaEscenarioError("Cada evento debe incluir 'id'.")
        try:
            return int(evento["id"])
        except (TypeError, ValueError) as error:
            raise PersistenciaEscenarioError("El id debe ser entero.") from error

    @staticmethod
    def _entidad(evento: object) -> Sismo:
        if not isinstance(evento, dict):
            raise PersistenciaEscenarioError("Cada evento debe ser un objeto.")
        try:
            clave_data = evento.get("clave")
            clave = tuple(clave_data) if clave_data is not None else None
            return Sismo(
                id=int(evento["id"]),
                magnitude=float(evento["magnitude"]),
                depth=float(evento["depth"]),
                epicenter_x=float(evento["epicenter_x"]),
                epicenter_y=float(evento["epicenter_y"]),
                timestamp=__import__("datetime").datetime.fromisoformat(
                    evento["timestamp"]
                ),
                revision=int(evento.get("revision", 1)),
                prioridad=(
                    int(evento["prioridad"])
                    if evento.get("prioridad") is not None else None
                ),
                clave=clave,
                reporting_stations=set(evento.get("reporting_stations", [])),
                status=StatusSismo(evento.get("status", StatusSismo.PENDIENTE.value)),
                estado_persistencia=EstadoPersistencia(
                    evento.get("estado_persistencia", EstadoPersistencia.ACTIVO.value)
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise PersistenciaEscenarioError(
                f"Evento inválido: {error}"
            ) from error

    @staticmethod
    def _validar_topologia(nodos: list) -> None:
        total = len(nodos)
        if not total:
            return
        referidos = set()
        for indice, nodo in enumerate(nodos):
            if not isinstance(nodo, dict) or not isinstance(nodo.get("clave"), list):
                raise PersistenciaEscenarioError(
                    f"Nodo {indice} inválido: se requiere clave."
                )
            if len(nodo["clave"]) != 3:
                raise PersistenciaEscenarioError("Cada clave debe tener tres valores.")
            for lado in ("izq", "der"):
                enlace = nodo.get(lado)
                if enlace is not None:
                    if not isinstance(enlace, int) or not 0 <= enlace < total:
                        raise PersistenciaEscenarioError(
                            f"Enlace {lado} inválido en nodo {indice}."
                        )
                    if enlace in referidos:
                        raise PersistenciaEscenarioError(
                            "La topología asigna un nodo a más de una posición."
                        )
                    referidos.add(enlace)
        if 0 in referidos:
            raise PersistenciaEscenarioError("La raíz no puede tener padre.")
        if len(referidos) != total - 1:
            raise PersistenciaEscenarioError(
                "La topología debe ser conexa y no puede contener ciclos."
            )
        visitados = set()

        def recorrer(indice, minimo=None, maximo=None):
            if indice is None:
                return
            if indice in visitados:
                raise PersistenciaEscenarioError(
                    "La topología contiene un ciclo."
                )
            visitados.add(indice)
            clave = tuple(nodos[indice]["clave"])
            if (minimo is not None and clave <= minimo) or (
                maximo is not None and clave >= maximo
            ):
                raise PersistenciaEscenarioError(
                    "Las claves de la topología no tienen orden global BST."
                )
            recorrer(nodos[indice].get("izq"), minimo, clave)
            recorrer(nodos[indice].get("der"), clave, maximo)

        recorrer(0)
        if len(visitados) != total:
            raise PersistenciaEscenarioError(
                "La topología contiene nodos no alcanzables desde la raíz."
            )
