import json
import math
import os
import re
from src.Models.Estaciones import Station


class StationValidationError(ValueError):
    """Excepción personalizada para errores de validación de negocio."""

    pass


ALLOWED_STATUSES = {"activa", "inactiva", "mantenimiento"}


class StationService:
    """Capa de negocio con validaciones, coordenadas únicas y almacenamiento JSON."""

    def __init__(self, json_file: str = "stations.json"):
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.json_file):
            self._write_raw_data([])

    def _write_raw_data(self, data: list):
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_data(self) -> list[Station]:
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

    def _save_data(self, stations: list[Station]):
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

    def _generate_next_id(self, stations_list: list[Station]) -> str:
        """Genera el siguiente ID como un número entero correlativo (1, 2, 3...)."""
        max_id = 0
        for s in stations_list:
            try:
                num_id = int(s.id)
                if num_id > max_id:
                    max_id = num_id
            except (ValueError, TypeError):
                continue

        return str(max_id + 1)

    def _check_duplicate_coordinates(
        self,
        lat: float,
        lon: float,
        stations_list: list[Station],
        current_station_id: str | None = None,
    ):
        """Verifica que no exista otra estación en las mismas coordenadas."""
        for s in stations_list:
            if current_station_id is not None and str(s.id).strip() == str(
                current_station_id
            ).strip():
                continue

            if math.isclose(s.lat, lat, abs_tol=1e-7) and math.isclose(
                s.lon, lon, abs_tol=1e-7
            ):
                raise StationValidationError(
                    f"Ya existe otra estación ('{s.name}', ID: {s.id}) en las coordenadas lat: {lat}, lon: {lon}."
                )

    def _sanitize_string(self, value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise StationValidationError(
                f"El campo '{field_name}' debe ser una cadena de texto."
            )

        clean = value.strip()
        clean = re.sub(r"<[^>]*>", "", clean)

        if not clean:
            raise StationValidationError(
                f"El campo '{field_name}' no puede estar vacío."
            )
        return clean

    def _validate_coordinates(self, lat: any, lon: any) -> tuple[float, float]:
        """Soporta enteros, flotantes y cadenas numéricas positivas o negativas."""
        try:
            val_lat = float(lat)
            val_lon = float(lon)
        except (ValueError, TypeError):
            raise StationValidationError(
                "Los campos 'lat' y 'lon' deben ser números válidos."
            )

        if math.isnan(val_lat) or math.isinf(val_lat) or math.isnan(val_lon) or math.isinf(val_lon):
            raise StationValidationError(
                "Las coordenadas no pueden ser NaN ni Infinito."
            )

        if not (-90.0 <= val_lat <= 90.0):
            raise StationValidationError(
                "La latitud debe estar entre -90.0 y 90.0."
            )

        if not (-180.0 <= val_lon <= 180.0):
            raise StationValidationError(
                "La longitud debe estar entre -180.0 y 180.0."
            )

        return val_lat, val_lon

    def _validate_coverage(self, coverage: any) -> float:
        try:
            val_coverage = float(coverage)
        except (ValueError, TypeError):
            raise StationValidationError(
                "El campo 'coverage' debe ser un número válido."
            )

        if math.isnan(val_coverage) or math.isinf(val_coverage):
            raise StationValidationError(
                "La cobertura no puede ser NaN ni Infinito."
            )

        if val_coverage < 0:
            raise StationValidationError(
                "La cobertura ('coverage') no puede ser un valor negativo."
            )

        return val_coverage

    def _validate_status(self, status: str) -> str:
        clean_status = self._sanitize_string(status, "status").lower()
        if clean_status not in ALLOWED_STATUSES:
            raise StationValidationError(
                f"Estado no válido. Opciones permitidas: {', '.join(ALLOWED_STATUSES)}"
            )
        return clean_status

    def get_all(self) -> list[Station]:
        return self._load_data()

    def get_by_id(self, station_id: str) -> Station | None:
        clean_id = station_id.strip()
        stations = self._load_data()
        return next((s for s in stations if s.id == clean_id), None)

    def _create_single(self, data: dict, stations_list: list[Station]) -> Station:
        if not isinstance(data, dict):
            raise StationValidationError(
                "Cada elemento debe ser un objeto JSON válido."
            )

        required_fields = ["name", "lat", "lon", "dept", "coverage"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise StationValidationError(
                f"Faltan campos obligatorios: {', '.join(missing)}"
            )

        lat, lon = self._validate_coordinates(data["lat"], data["lon"])
        self._check_duplicate_coordinates(lat, lon, stations_list)

        station_id = self._generate_next_id(stations_list)

        name = self._sanitize_string(data["name"], "name")
        dept = self._sanitize_string(data["dept"], "dept")
        coverage = self._validate_coverage(data["coverage"])
        status = self._validate_status(data.get("status", "activa"))

        new_station = Station(
            id=station_id,
            name=name,
            lat=lat,
            lon=lon,
            status=status,
            dept=dept,
            coverage=coverage,
        )
        stations_list.append(new_station)
        return new_station

    def create(self, data: dict | list) -> Station | list[Station]:
        stations = self._load_data()

        if isinstance(data, list):
            if not data:
                raise StationValidationError(
                    "La lista de estaciones no puede estar vacía."
                )

            new_stations = []
            for item in data:
                created = self._create_single(item, stations)
                new_stations.append(created)

            self._save_data(stations)
            return new_stations

        if isinstance(data, dict):
            new_station = self._create_single(data, stations)
            self._save_data(stations)
            return new_station

        raise StationValidationError(
            "El cuerpo de la petición debe ser un objeto o arreglo JSON."
        )

    def update(self, station_id: str, data: dict) -> Station | None:
        if not isinstance(data, dict):
            raise StationValidationError(
                "El cuerpo de la petición debe ser un objeto JSON."
            )

        clean_id = station_id.strip()
        stations = self._load_data()
        target_station = next((s for s in stations if s.id == clean_id), None)

        if not target_station:
            return None

        if "lat" in data or "lon" in data:
            new_lat = data.get("lat", target_station.lat)
            new_lon = data.get("lon", target_station.lon)
            val_lat, val_lon = self._validate_coordinates(new_lat, new_lon)

            self._check_duplicate_coordinates(
                val_lat, val_lon, stations, current_station_id=clean_id
            )

            target_station.lat = val_lat
            target_station.lon = val_lon

        if "name" in data:
            target_station.name = self._sanitize_string(data["name"], "name")

        if "dept" in data:
            target_station.dept = self._sanitize_string(data["dept"], "dept")

        if "coverage" in data:
            target_station.coverage = self._validate_coverage(data["coverage"])

        if "status" in data:
            target_station.status = self._validate_status(data["status"])

        self._save_data(stations)
        return target_station

    def delete(self, station_id: str) -> bool:
        clean_id = station_id.strip()
        stations = self._load_data()
        filtered = [s for s in stations if s.id != clean_id]

        if len(filtered) < len(stations):
            self._save_data(filtered)
            return True
        return False