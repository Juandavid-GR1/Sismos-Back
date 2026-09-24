from datetime import datetime
import math
from typing import Protocol, Optional
from src.Models.Sismo import Sismo, StatusSismo


class SismoValidationError(ValueError):
    """Excepción para errores de validación de negocio en Sismos."""
    pass


class SismoNotFoundError(KeyError):
    """Excepción lanzada cuando no se encuentra un evento sísmico."""
    pass


class ISismoRepository(Protocol):
    """Interfaz (Protocolo) para abstraer la capa de persistencia."""

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        ...

    def get_all(self) -> list[Sismo]:
        ...

    def save(self, sismo: Sismo) -> Sismo:
        ...

    def delete(self, sismo_id: int) -> bool:
        ...

    def generate_next_id(self) -> int:
        ...


class SismoService:
    """
    Capa de servicio para la entidad Sismo.
    Implementa las reglas de negocio, consenso de estaciones, control de revisiones y validaciones.
    """

    def __init__(self, repository: ISismoRepository):
        self.repository = repository

    # --- Métodos de Validación ---

    def _validate_id(self, sismo_id: any) -> int:
        try:
            val_id = int(sismo_id)
        except (ValueError, TypeError):
            raise SismoValidationError("El 'id' debe ser un número entero.")

        if not (1 <= val_id <= 999999):
            raise SismoValidationError("El 'id' debe estar entre 1 y 999999.")
        return val_id

    def _validate_magnitude(self, magnitude: any) -> float:
        try:
            val = round(float(magnitude), 1)
        except (ValueError, TypeError):
            raise SismoValidationError("La 'magnitude' debe ser un número válido.")

        if not (-2.0 <= val <= 10.0):
            raise SismoValidationError("La magnitud debe estar entre -2.0 y 10.0.")
        return val

    def _validate_depth(self, depth: any) -> float:
        try:
            val = round(float(depth), 1)
        except (ValueError, TypeError):
            raise SismoValidationError("La profundidad 'depth' debe ser un número válido.")

        if not (0.0 <= val <= 700.0):
            raise SismoValidationError("La profundidad debe estar entre 0.0 y 700.0 km.")
        return val

    def _validate_epicenter_coord(self, coord: any, name: str) -> float:
        try:
            return round(float(coord), 6)
        except (ValueError, TypeError):
            raise SismoValidationError(f"La coordenada '{name}' debe ser un número válido.")

    def _validate_timestamp(self, ts: any) -> datetime:
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                raise SismoValidationError("El 'timestamp' debe ser una cadena con formato ISO 8601 válido.")
        raise SismoValidationError("El 'timestamp' debe ser un objeto datetime o una cadena ISO 8601.")

    def _validate_station_id(self, station_id: Optional[str]) -> Optional[str]:
        """Acepta un identificador opcional. Retorna None si no se envía o es una cadena vacía."""
        if station_id is None:
            return None
        if not isinstance(station_id, str):
            raise SismoValidationError("El identificador de estación debe ser una cadena de texto.")
        
        cleaned = station_id.strip()
        return cleaned if cleaned else None

    # --- Reglas de Negocio Principales ---

    def create_event(
        self,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
        initial_station_id: Optional[str] = None,
    ) -> Sismo:
        """
        1. Alta Inicial (Revisión 1):
           Crea un nuevo evento con revision=1, status=PENDIENTE. La estación emisora es opcional.
        """
        station = self._validate_station_id(initial_station_id)
        sismo_id = self.repository.generate_next_id()
        self._validate_id(sismo_id)

        sismo = Sismo(
            id=sismo_id,
            magnitude=self._validate_magnitude(magnitude),
            depth=self._validate_depth(depth),
            epicenter_x=self._validate_epicenter_coord(epicenter_x, "epicenter_x"),
            epicenter_y=self._validate_epicenter_coord(epicenter_y, "epicenter_y"),
            timestamp=self._validate_timestamp(timestamp),
            revision=1,
            reporting_stations={station} if station else set(),
            status=StatusSismo.PENDIENTE,
        )

        return self.repository.save(sismo)

    def add_consensus_report(self, sismo_id: int, station_id: str) -> Sismo:
        station = self._validate_station_id(station_id)
        if not station:
            raise SismoValidationError("El identificador de la estación no puede estar vacío.")

        sismo = self.repository.get_by_id(self._validate_id(sismo_id))
        if not sismo:
            raise SismoNotFoundError(f"No existe el evento sísmico con ID {sismo_id}.")

        sismo.reporting_stations.add(station)
        return self.repository.save(sismo)

    def apply_correction(
        self,
        sismo_id: int,
        station_id: str,
        magnitude: Optional[float] = None,
        depth: Optional[float] = None,
        epicenter_x: Optional[float] = None,
        epicenter_y: Optional[float] = None,
    ) -> Sismo:
        station = self._validate_station_id(station_id)
        if not station:
            raise SismoValidationError("El identificador de la estación no puede estar vacío al aplicar corrección.")

        sismo = self.repository.get_by_id(self._validate_id(sismo_id))
        if not sismo:
            raise SismoNotFoundError(f"No existe el evento sísmico con ID {sismo_id}.")

        new_mag = self._validate_magnitude(magnitude) if magnitude is not None else sismo.magnitude
        new_depth = self._validate_depth(depth) if depth is not None else sismo.depth
        new_x = self._validate_epicenter_coord(epicenter_x, "epicenter_x") if epicenter_x is not None else sismo.epicenter_x
        new_y = self._validate_epicenter_coord(epicenter_y, "epicenter_y") if epicenter_y is not None else sismo.epicenter_y

        has_changed = not (
            math.isclose(sismo.magnitude, new_mag, abs_tol=1e-1)
            and math.isclose(sismo.depth, new_depth, abs_tol=1e-1)
            and math.isclose(sismo.epicenter_x, new_x, abs_tol=1e-1)
            and math.isclose(sismo.epicenter_y, new_y, abs_tol=1e-1)
        )

        if has_changed:
            sismo.magnitude = new_mag
            sismo.depth = new_depth
            sismo.epicenter_x = new_x
            sismo.epicenter_y = new_y
            sismo.revision += 1
            sismo.status = StatusSismo.PENDIENTE
            sismo.reporting_stations = {station}

            return self.repository.save(sismo)

        return self.add_consensus_report(sismo_id, station_id)

    def audit_and_validate(self, sismo_id: int) -> Sismo:
        sismo = self.repository.get_by_id(self._validate_id(sismo_id))

        if not sismo:
            raise SismoNotFoundError(f"No existe el evento sísmico con ID {sismo_id}.")

        sismo.status = StatusSismo.CONFIRMADO
        return self.repository.save(sismo)

    def delete(self, sismo_id: any) -> bool:
        """
        Valida el ID del sismo, confirma su existencia y solicita su eliminación al repositorio.
        """
        val_id = self._validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(f"No existe el evento sísmico con ID {val_id}.")

        return self.repository.delete(val_id)

    # Alias alternativo
    delete_event = delete

    def get_by_id(self, sismo_id: int) -> Sismo:
        sismo = self.repository.get_by_id(self._validate_id(sismo_id))
        if not sismo:
            raise SismoNotFoundError(f"No se encontró el evento sísmico con ID {sismo_id}.")
        return sismo

    def get_all(self) -> list[Sismo]:
        return self.repository.get_all()