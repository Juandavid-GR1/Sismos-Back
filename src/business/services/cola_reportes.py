from src.estructuras.cola import Cola
from src.business.interfaces.IF_Colas import ColaPersistencia


class ColaReportesService:

    def __init__(self, persistencia: ColaPersistencia):
        self.cola = Cola()
        self.persistencia = persistencia
        self._recuperar_reportes()

    def _recuperar_reportes(self):
        reportes = self.persistencia.cargar()

        for reporte in reportes:
            self.cola.encolar(reporte)

    def agregar_reporte(self, reporte):
        self.cola.encolar(reporte)
        self._guardar_cola()

    def obtener_siguiente(self):
        reporte = self.cola.desencolar()
        self._guardar_cola()
        return reporte

    def obtener_frente(self):
        return self.cola.frente()

    def obtener_cola(self):
        return self.cola.obtener_elementos()

    def esta_vacia(self):
        return self.cola.estaVacia()

    def descartar_reporte(self):
        """
        Elimina el primer reporte de la cola.
        """
        reporte = self.cola.desencolar()

        self._guardar_cola()

        return reporte

    def _guardar_cola(self):
        reportes = self.cola.obtener_elementos()
        self.persistencia.guardar(reportes)