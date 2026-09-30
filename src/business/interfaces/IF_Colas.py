from abc import ABC, abstractmethod


class ColaPersistencia(ABC):

    @abstractmethod
    def guardar(self, reportes):
        pass

    @abstractmethod
    def cargar(self):
        pass