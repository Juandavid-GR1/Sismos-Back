import copy
import json
from datetime import datetime

from src.estructuras.pila import Pila


class EstadoService:
    """Captures and restores the complete operational state."""

    def __init__(self, sismo_repository, avl_service, eliminados_service,
                 sismo_service, reloj_service, cola_reportes):
        self.repo = sismo_repository
        self.avl = avl_service
        self.eliminados = eliminados_service
        self.sismos = sismo_service
        self.reloj = reloj_service
        self.cola = cola_reportes

    def capturar(self) -> dict:
        arbol = self.avl.get_arbol()
        return {
            "sismos": self.repo.exportar(),
            "arbol": {
                "nodos": arbol.exportarTopologia(),
                "modoEstres": arbol.esModoEstres(),
                "contadores": arbol.getContadores(),
            },
            "eliminados": sorted(self.eliminados.todos()),
            "metricas": dict(self.sismos.contadores),
            "reloj": self.reloj.obtener_reloj().isoformat(),
            "cola": self.cola.exportar(),
        }

    def restaurar(self, estado: dict) -> None:
        estado = copy.deepcopy(estado)     
        self.repo.reemplazar_todo(estado["sismos"])
        self.avl.get_arbol().importarTopologia(
            estado["arbol"]["nodos"], estado["arbol"]["modoEstres"], estado["arbol"]["contadores"]
        )
        self.eliminados.reemplazar(estado["eliminados"])
        self.sismos.contadores = dict(estado["metricas"])
        self.reloj.restaurar(datetime.fromisoformat(estado["reloj"]))
        self.cola.reemplazar(estado["cola"])

    @staticmethod
    def huella(estado: dict) -> str:
        """Canonical text used to know whether an action changed anything."""
        return json.dumps(estado, sort_keys=True, default=str)


class HistorialService:
    """Undo stack of actions."""

    LIMITE_ACCIONES = 200

    def __init__(self, estado_service: EstadoService):
        self.estado = estado_service
        self._pila = Pila()
        self._secuencia = 0

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
        self.estado.restaurar(accion["estado"])
        return self._resumen(accion)

    def listar(self) -> list:
        return [self._resumen(a) for a in self._pila.elementos()]

    def vaciar(self):
        self._pila.vaciar()

    @staticmethod
    def _resumen(accion: dict) -> dict:
        return {k: accion[k] for k in ("numero", "descripcion", "hora")}