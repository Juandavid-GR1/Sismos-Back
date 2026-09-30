"""
RelojService

Reloj de simulación explícito del escenario (sección 3 del enunciado):
"El reloj de simulación es explícito y se guarda con el escenario. Los
tiempos de ocurrencia no pueden ser posteriores a ese reloj. Su avance
se realiza por una acción del usuario y determina la antigüedad de
los eventos."

Este servicio NO valida sismos -- solo mantiene el reloj y expone la
comparación que otros servicios (SismoService, y más adelante el
archivo de rama de la sección 10) necesitan.
"""

from datetime import datetime, timedelta


class RelojFueraDeOrdenError(ValueError):
    """Se lanza si se intenta mover el reloj hacia atrás -- un "avance"
    nunca debería retroceder el tiempo del escenario."""
    pass


def _normalizar(fecha_hora: datetime) -> datetime:
    """Quita la zona horaria si la trae (offset-aware -> offset-naive).

    El frontend puede enviar timestamps con 'Z' (UTC explícito, ej.
    desde new Date().toISOString()) o sin ella -- Python no permite
    comparar un datetime "aware" contra uno "naive" con < > ==, así
    que todo se normaliza a naive ANTES de comparar. El proyecto no
    necesita manejar zonas horarias reales (territorio ficticio), así
    que se descarta el offset en vez de convertir --  simplifica sin
    perder nada relevante para el escenario."""
    if fecha_hora.tzinfo is not None:
        return fecha_hora.replace(tzinfo=None)
    return fecha_hora


class RelojService:

    def __init__(self, hora_inicial: datetime = None):
        base = hora_inicial if hora_inicial is not None else datetime.now()
        self._reloj_actual = _normalizar(base)

    def obtener_reloj(self) -> datetime:
        return self._reloj_actual

    def avanzar_a(self, nueva_fecha_hora: datetime) -> datetime:
        """Mueve el reloj a una fecha/hora absoluta. Debe ser
        estrictamente posterior (o igual) a la actual."""
        nueva_fecha_hora = _normalizar(nueva_fecha_hora)
        if nueva_fecha_hora < self._reloj_actual:
            raise RelojFueraDeOrdenError(
                f"No se puede retroceder el reloj: la nueva fecha ({nueva_fecha_hora}) "
                f"es anterior a la actual ({self._reloj_actual})."
            )
        self._reloj_actual = nueva_fecha_hora
        return self._reloj_actual

    def avanzar_horas(self, horas: float) -> datetime:
        """Conveniencia: avanza el reloj un número de horas (puede ser
        fraccionario) respecto a su valor actual."""
        if horas < 0:
            raise RelojFueraDeOrdenError(
                "No se puede avanzar el reloj un número negativo de horas."
            )
        nueva_fecha = self._reloj_actual + timedelta(hours=horas)
        return self.avanzar_a(nueva_fecha)

    def es_posterior_al_reloj(self, fecha_hora: datetime) -> bool:
        """True si fecha_hora ocurre DESPUÉS del reloj actual -- usado
        para validar que ningún evento tenga un timestamp futuro
        respecto al escenario."""
        return _normalizar(fecha_hora) > self._reloj_actual

    def antiguedad_en_horas(self, fecha_hora: datetime) -> float:
        """Diferencia en horas entre el reloj actual y fecha_hora --
        necesaria más adelante para el archivo de rama (sección 10:
        'antigüedad estrictamente mayor a T horas')."""
        diferencia = self._reloj_actual - _normalizar(fecha_hora)
        return diferencia.total_seconds() / 3600