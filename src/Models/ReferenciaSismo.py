from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReferenciaSismo:
    """
    Relación entre un sismo y su único sismo de referencia.

    Un sismo puede tener como máximo una referencia.
    Un mismo sismo puede ser referencia de múltiples sismos.
    """

    sismo_id: int
    referencia_id: int
    distancia: float
    fecha_creacion: datetime

    def to_dict(self):
        return {
            "sismo_id": self.sismo_id,
            "referencia_id": self.referencia_id,
            "distancia": self.distancia,
            "fecha_creacion": self.fecha_creacion.isoformat()
        }