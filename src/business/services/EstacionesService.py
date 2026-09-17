import math
import re
from src.business.interfaces.IF_Estaciones import IF_Estaciones
from src.Models.Estaciones import Station


class StationValidationError(ValueError):
    """Excepción personalizada para errores de validación de negocio."""

    pass


ALLOWED_STATUSES = {"activa", "inactiva", "mantenimiento"}


class StationService:
    """Capa de negocio pura con validaciones e inyección de dependencia."""

    def __init__(self, repository: IF_Estaciones):
        self.repository = repository

    def _generate_next_id(self, stations_list: list[Station]) -> str:
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
        return self.repository.get_all()

    def get_by_id(self, station_id: str) -> Station | None:
        clean_id = station_id.strip()
        stations = self.repository.get_all()
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
        stations = self.repository.get_all()

        if isinstance(data, list):
            if not data:
                raise StationValidationError(
                    "La lista de estaciones no puede estar vacía."
                )

            new_stations = []
            for item in data:
                created = self._create_single(item, stations)
                new_stations.append(created)

            self.repository.save_all(stations)
            return new_stations

        if isinstance(data, dict):
            new_station = self._create_single(data, stations)
            self.repository.save_all(stations)
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
        stations = self.repository.get_all()
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

        self.repository.save_all(stations)
        return target_station

    def delete(self, station_id: str) -> bool:
        clean_id = station_id.strip()
        stations = self.repository.get_all()
        filtered = [s for s in stations if s.id != clean_id]

        if len(filtered) < len(stations):
            self.repository.save_all(filtered)
            return True
        return False