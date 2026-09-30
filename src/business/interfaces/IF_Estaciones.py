from abc import ABC, abstractmethod
from src.Models.Estaciones import Station


class IF_Estaciones(ABC):
    """Interfaz abstracta para el almacenamiento de estaciones."""

    @abstractmethod
    def get_all(self) -> list[Station]:
        """Obtiene todas las estaciones guardadas."""
        pass

    @abstractmethod
    def save_all(self, stations: list[Station]) -> None:
        """Guarda la lista completa de estaciones."""
        pass