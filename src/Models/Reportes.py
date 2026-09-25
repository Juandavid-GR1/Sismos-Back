from dataclasses import dataclass
from datetime import datetime


@dataclass
class Reporte:
    """
    Representa el reporte de una estación sobre un sismo existente.
    """

    sismo_id: int
    station_id: str
    magnitude: float
    depth: float
    epicenter_x: float
    epicenter_y: float
    timestamp: datetime