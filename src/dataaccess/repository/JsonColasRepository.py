import json
import os
from datetime import datetime

from src.Models.Reportes import Reporte
from src.business.interfaces.IF_Colas import ColaPersistencia


class ColaJsonPersistencia(ColaPersistencia):

    def __init__(self, ruta="data/reportes_cola.json"):
        self.ruta = ruta
        self._crear_archivo()

    def _crear_archivo(self):
        carpeta = os.path.dirname(self.ruta)

        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        if not os.path.exists(self.ruta):
            with open(self.ruta, "w", encoding="utf-8") as archivo:
                json.dump([], archivo, ensure_ascii=False, indent=4)

    def guardar(self, reportes):
        datos = [
            self._reporte_a_dict(reporte)
            for reporte in reportes
        ]

        with open(self.ruta, "w", encoding="utf-8") as archivo:
            json.dump(
                datos,
                archivo,
                ensure_ascii=False,
                indent=4
            )

    def cargar(self):
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            return [
                self._dict_a_reporte(data)
                for data in datos
            ]

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _reporte_a_dict(self, reporte: Reporte):
        return {
            "sismo_id": reporte.sismo_id,
            "station_id": reporte.station_id,
            "magnitude": reporte.magnitude,
            "depth": reporte.depth,
            "epicenter_x": reporte.epicenter_x,
            "epicenter_y": reporte.epicenter_y,
            "timestamp": reporte.timestamp.isoformat()
        }

    def _dict_a_reporte(self, data):
        return Reporte(
            sismo_id=data["sismo_id"],
            station_id=data["station_id"],
            magnitude=data["magnitude"],
            depth=data["depth"],
            epicenter_x=data["epicenter_x"],
            epicenter_y=data["epicenter_y"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )