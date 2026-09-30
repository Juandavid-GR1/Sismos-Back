from datetime import datetime
from typing import Optional, Any


class SismoValidationError(ValueError):
    """Excepción para errores de validación de negocio en Sismos."""
    pass


class SismoValidationService:

    @staticmethod
    def validate_id(
        sismo_id: Any
    ) -> int:

        try:
            val_id = int(sismo_id)
        except (ValueError, TypeError):
            raise SismoValidationError(
                "El 'id' debe ser un número entero."
            )

        if not (1 <= val_id <= 999999):
            raise SismoValidationError(
                "El 'id' debe estar entre 1 y 999999."
            )

        return val_id

    @staticmethod
    def validate_magnitude(
        magnitude: Any
    ) -> float:

        try:
            val = round(
                float(magnitude),
                1
            )
        except (ValueError, TypeError):
            raise SismoValidationError(
                "La 'magnitude' debe ser un número válido."
            )

        if not (-2.0 <= val <= 10.0):
            raise SismoValidationError(
                "La magnitud debe estar entre -2.0 y 10.0."
            )

        return val

    @staticmethod
    def validate_depth(
        depth: Any
    ) -> float:

        try:
            val = round(
                float(depth),
                1
            )
        except (ValueError, TypeError):
            raise SismoValidationError(
                "La profundidad 'depth' debe ser un número válido."
            )

        if not (0.0 <= val <= 700.0):
            raise SismoValidationError(
                "La profundidad debe estar entre 0.0 y 700.0 km."
            )

        return val

    @staticmethod
    def validate_epicenter_coord(
        coord: Any,
        name: str
    ) -> float:

        try:
            value = round(
                float(coord),
                6
            )
        except (ValueError, TypeError):
            raise SismoValidationError(
                f"La coordenada '{name}' debe ser un número válido."
            )

        if name == "epicenter_x":
            if not -180.0 <= value <= 180.0:
                raise SismoValidationError(
                    "La longitud debe estar entre -180.0 y 180.0 grados."
                )

        elif name == "epicenter_y":
            if not -90.0 <= value <= 90.0:
                raise SismoValidationError(
                    "La latitud debe estar entre -90.0 y 90.0 grados."
                )

        return value

    @staticmethod
    def validate_timestamp(
        ts: Any
    ) -> datetime:

        if isinstance(ts, datetime):
            return ts

        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                raise SismoValidationError(
                    "El 'timestamp' debe ser una cadena con formato ISO 8601 válido."
                )

        raise SismoValidationError(
            "El 'timestamp' debe ser un objeto datetime o una cadena ISO 8601."
        )

    @staticmethod
    def validate_station_id(
        station_id: Optional[str]
    ) -> Optional[str]:

        if station_id is None:
            return None

        if not isinstance(station_id, str):
            raise SismoValidationError(
                "El identificador de estación debe ser una cadena de texto."
            )

        cleaned = station_id.strip()

        return cleaned if cleaned else None

    @staticmethod
    def validate_priority(
        prioridad: Optional[int]
    ) -> Optional[int]:

        if prioridad is None:
            return None

        if not isinstance(prioridad, int):
            raise SismoValidationError(
                "La prioridad debe ser un número entero."
            )

        if prioridad not in (1, 2, 3):
            raise SismoValidationError(
                "La prioridad debe ser 1, 2 o 3."
            )

        return prioridad

    @staticmethod
    def validate_key(
        clave: Optional[tuple[int, float, int]]
    ) -> Optional[tuple[int, float, int]]:

        if clave is None:
            return None

        if not isinstance(clave, tuple):
            raise SismoValidationError(
                "La clave del sismo debe ser una tupla."
            )

        if len(clave) != 3:
            raise SismoValidationError(
                "La clave debe tener el formato (P, M, I)."
            )

        prioridad, magnitude, sismo_id = clave

        if not isinstance(prioridad, int):
            raise SismoValidationError(
                "El primer elemento de la clave debe ser la prioridad."
            )

        if prioridad not in (1, 2, 3):
            raise SismoValidationError(
                "La prioridad de la clave debe ser 1, 2 o 3."
            )

        try:
            magnitude = float(magnitude)
        except (ValueError, TypeError):
            raise SismoValidationError(
                "El segundo elemento de la clave debe ser la magnitud."
            )

        try:
            sismo_id = int(sismo_id)
        except (ValueError, TypeError):
            raise SismoValidationError(
                "El tercer elemento de la clave debe ser el ID del sismo."
            )

        return (
            prioridad,
            magnitude,
            sismo_id
        )