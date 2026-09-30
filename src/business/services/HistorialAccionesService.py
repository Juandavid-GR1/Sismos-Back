from src.estructuras.pila import Pila
from src.dataaccess.repository.HistorialAccionesRepository import (
    HistorialAccionesRepository,
)
from src.Models.AccionSismo import AccionSismo


class HistorialAccionesService:
    """LIFO history for atomic deletion and archive actions.

    When a repository is supplied, snapshots survive process restarts.
    """

    def __init__(
        self,
        repository: HistorialAccionesRepository | None = None,
    ) -> None:
        self._acciones = Pila()
        self.repository = repository
        if self.repository is not None:
            for accion in reversed(self.repository.cargar()):
                self._acciones.apilar(accion)

    def registrar(self, accion: AccionSismo) -> None:
        self._acciones.apilar(accion)
        try:
            self._persistir()
        except Exception:
            self._acciones.desapilar()
            raise

    def deshacer_ultima(self) -> AccionSismo:
        if self._acciones.estaVacia():
            raise LookupError("No hay acciones para deshacer.")
        return self._acciones.desapilar()

    def confirmar_deshacer(self) -> None:
        """Persists the stack after the domain restoration succeeds."""
        self._persistir()

    def cantidad(self) -> int:
        return len(self._acciones)

    def _persistir(self) -> None:
        if self.repository is not None:
            self.repository.guardar(self._acciones.obtener_elementos())
