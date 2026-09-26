from datetime import datetime
import json
import os
from typing import List, Optional

from src.Models.Sismo import Sismo, StatusSismo
from src.business.interfaces.IF_Sismos import IF_Sismos


class SismoJsonRepository(IF_Sismos):
    """Implementación concreta de IF_Sismos que almacena los eventos sísmicos en un archivo JSON."""

    def __init__(self, json_file: str = "sismos.json") -> None:
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Crea el archivo JSON si no existe en el sistema de archivos."""
        if not os.path.exists(self.json_file):
            self._write_raw_data([])

    def _write_raw_data(self, data: List[dict]) -> None:
        """Escribe directamente la estructura de diccionarios en el archivo JSON."""
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _to_dict(self, sismo: Sismo) -> dict:
        """Convierte una entidad Sismo a un diccionario serializable en JSON."""
        return {
            "id": sismo.id,
            "magnitude": sismo.magnitude,
            "depth": sismo.depth,
            "epicenter_x": sismo.epicenter_x,
            "epicenter_y": sismo.epicenter_y,
            "timestamp": sismo.timestamp.isoformat(),
            "revision": sismo.revision,
            "prioridad": sismo.prioridad,
            "clave": list(sismo.clave) if sismo.clave is not None else None,
            "reporting_stations": list(sismo.reporting_stations),
            "status": sismo.status.value,
        }

    def _to_entity(self, data: dict) -> Sismo:
        """Reconstruye una entidad Sismo desde un diccionario cargado de JSON."""
        clave_data = data.get("clave")
        clave = (
            (int(clave_data[0]), float(clave_data[1]), int(clave_data[2]))
            if clave_data is not None
            else None
        )

        return Sismo(
            id=int(data["id"]),
            magnitude=float(data["magnitude"]),
            depth=float(data["depth"]),
            epicenter_x=float(data["epicenter_x"]),
            epicenter_y=float(data["epicenter_y"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            revision=int(data.get("revision", 0)),
            prioridad=int(data["prioridad"]) if data.get("prioridad") is not None else None,
            clave=clave,
            reporting_stations=set(data.get("reporting_stations", [])),
            status=StatusSismo(data.get("status", StatusSismo.PENDIENTE.value)),
        )

    def get_all(self) -> List[Sismo]:
        """Lee el archivo JSON y retorna la lista de instancias Sismo."""
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, list):
                return []

            return [self._to_entity(item) for item in raw_data]

        except (json.JSONDecodeError, KeyError, ValueError, TypeError, IndexError):
            return []

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """Busca un sismo por su ID."""
        return next((s for s in self.get_all() if s.id == sismo_id), None)

    def save(self, sismo: Sismo) -> Sismo:
        """Inserta o actualiza un sismo en el archivo JSON."""
        sismos = self.get_all()
        updated = False

        for i, existing in enumerate(sismos):
            if existing.id == sismo.id:
                sismos[i] = sismo
                updated = True
                break

        if not updated:
            sismos.append(sismo)

        self._write_raw_data([self._to_dict(s) for s in sismos])
        return sismo

    def delete(self, sismo_id: int) -> bool:
        """Elimina un evento sísmico del archivo JSON por su ID."""
        sismos = self.get_all()
        filtered_sismos = [s for s in sismos if s.id != sismo_id]

        if len(filtered_sismos) == len(sismos):
            return False

        self._write_raw_data([self._to_dict(s) for s in filtered_sismos])
        return True

    def generate_next_id(self) -> int:
        """Calcula el siguiente ID numérico disponible."""
        sismos = self.get_all()
        if not sismos:
            return 1
        return max(s.id for s in sismos) + 1