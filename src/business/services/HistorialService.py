import copy
import json
from datetime import datetime

from src.estructuras.pila import Pila


class EstadoService:
    """Captures and restores the complete operational state."""

    def __init__(self, sismo_repository, avl_service, eliminados_service,
                 sismo_service, reloj_service, cola_reportes,
                 historial_repository, referencias_repository=None,
                 zonas_repository=None):
        self.repo = sismo_repository
        self.avl = avl_service
        self.eliminados = eliminados_service
        self.sismos = sismo_service
        self.reloj = reloj_service
        self.cola = cola_reportes
        self.historial = historial_repository
        self.referencias = referencias_repository
        self.zonas = zonas_repository
        self.configuracion = None

    def conectar_configuracion(self, configuracion):
        self.configuracion = configuracion

    def capturar(self) -> dict:
        arbol = self.avl.get_arbol()
        return {
            "sismos": self.repo.exportar(),
            "historico": self.historial.exportar(),
            "arbol": {
                "nodos": arbol.exportarTopologia(),
                "modoEstres": arbol.esModoEstres(),
                "contadores": arbol.getContadores(),
            },
            "eliminados": sorted(self.eliminados.todos()),
            "metricas": dict(self.sismos.contadores),
            "reloj": self.reloj.obtener_reloj().isoformat(),
            "cola": self.cola.exportar(),
            "referencias": (
                self.referencias.exportar()
                if self.referencias is not None else {}
            ),
            "configuracion": (
                self.configuracion.exportar()
                if self.configuracion is not None else {}
            ),
            "zonas": (
                self.zonas.get_all()
                if self.zonas is not None else {}
            ),
        }

    def restaurar(self, estado: dict) -> None:
        estado = copy.deepcopy(estado)     
        self.repo.reemplazar_todo(estado["sismos"])
        self.historial.reemplazar_todo(estado.get("historico", []))
        self.avl.get_arbol().importarTopologia(
            estado["arbol"]["nodos"], estado["arbol"]["modoEstres"], estado["arbol"]["contadores"]
        )
        self.eliminados.reemplazar(estado["eliminados"])
        self.sismos.contadores = dict(estado["metricas"])
        self.reloj.restaurar(datetime.fromisoformat(estado["reloj"]))
        self.cola.reemplazar(estado["cola"])
        if self.referencias is not None and "referencias" in estado:
            self.referencias.reemplazar_todo(estado.get("referencias", {}))
        if self.configuracion is not None and "configuracion" in estado:
            self.configuracion.reemplazar(estado["configuracion"])
        if self.zonas is not None and "zonas" in estado:
            self.zonas.reemplazar_todo(estado["zonas"])

    @staticmethod
    def huella(estado: dict) -> str:
        """Canonical text used to know whether an action changed anything."""
        return json.dumps(estado, sort_keys=True, default=str)


class HistorialService:
    """Undo stack of actions."""

    LIMITE_ACCIONES = 200

    def __init__(self, estado_service: EstadoService, repository=None):
        self.estado = estado_service
        self._pila = Pila()
        self._secuencia = 0
        self.repository = repository
        acciones = repository.cargar() if repository is not None else []
        for accion in acciones:
            self._pila.apilar(accion)
            self._secuencia = max(self._secuencia, int(accion.get("numero", 0)))

    def registrar(self, descripcion: str, estado_anterior: dict) -> dict:
        self._secuencia += 1
        accion = {
            "numero": self._secuencia,
            "descripcion": descripcion,
            "hora": datetime.now().strftime("%H:%M:%S"),
            "estado": estado_anterior,
        }
        self._pila.apilar(accion)
        if len(self._pila) > self.LIMITE_ACCIONES:
            self._recortar()
        self._persistir()
        return self._resumen(accion)

    def _recortar(self):
        conservar = self._pila.elementos()[: self.LIMITE_ACCIONES]
        self._pila.vaciar()
        for accion in reversed(conservar):
            self._pila.apilar(accion)

    def deshacer(self) -> dict | None:
        """Restores the state before the last action. None if empty."""
        if self._pila.estaVacia():
            return None
        accion = self._pila.desapilar()
        try:
            self.estado.restaurar(accion["estado"])
            self._persistir()
        except Exception:
            self._pila.apilar(accion)
            raise
        return self._resumen(accion)

    def listar(self) -> list:
        return [self._resumen(a) for a in self._pila.elementos()]

    def vaciar(self):
        self._pila.vaciar()
        self._persistir()

    def _persistir(self):
        if self.repository is not None:
            # The JSON file is stored from the oldest action (base) to the
            # newest action (top), while Pila exposes the opposite order.
            self.repository.guardar(list(reversed(self._pila.elementos())))

    @staticmethod
    def _resumen(accion: dict) -> dict:
        return {k: accion[k] for k in ("numero", "descripcion", "hora")}