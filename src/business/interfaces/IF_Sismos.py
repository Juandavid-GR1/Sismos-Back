from abc import ABC, abstractmethod
from typing import Optional
from src.Models.Sismo import Sismo


class IF_Sismos(ABC):
    """
    Interfaz abstracta que define el contrato de almacenamiento para la entidad Sismo.
    Cualquier mecanismo de persistencia (JSON, SQL, MongoDB, Memoria) debe implementarla.
    """

    @abstractmethod
    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """Obtiene un sismo por su ID numérico. Retorna None si no existe."""
        pass

    @abstractmethod
    def get_all(self) -> list[Sismo]:
        """Obtiene la lista completa de eventos sísmicos."""
        pass

    @abstractmethod
    def save(self, sismo: Sismo) -> Sismo:
        """Guarda o actualiza una instancia de Sismo."""
        pass

    @abstractmethod
    def generate_next_id(self) -> int:
        """Genera el siguiente ID numérico autoincremental único."""
        pass