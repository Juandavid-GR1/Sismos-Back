import json
import os
from src.business.interfaces.IF_Estaciones import IF_Estaciones
from src.Models.Estaciones import Station


class JsonStationRepository(IF_Estaciones):
    """Implementación de la interfaz para persistencia física en archivo JSON."""

    def __init__(self, json_file: str = "data/stations.json"):
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.json_file):
            self._write_raw_data([])

    def _write_raw_data(self, data: list):
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all(self) -> list[Station]:
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return [
                    Station(
                        id=str(item.get("id", "")),
                        name=str(item.get("name", "")),
                        lat=float(item.get("lat", 0.0)),
                        lon=float(item.get("lon", 0.0)),
                        status=str(item.get("status", "activa")),
                        dept=str(item.get("dept", "")),
                        coverage=float(item.get("coverage", 0.0)),
                    )
                    for item in data
                ]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def save_all(self, stations: list[Station]) -> None:
        data = [
            {
                "id": s.id,
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "status": s.status,
                "dept": s.dept,
                "coverage": s.coverage,
            }
            for s in stations
        ]
        self._write_raw_data(data)