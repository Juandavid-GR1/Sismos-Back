from dataclasses import replace
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
        self._cache: Optional[dict] = None
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

    # ------------------------------------------------------------------
    # In-memory cache (write-through)
    #
    # The previous version re-read and re-parsed the whole JSON file on
    # EVERY get_by_id/save (O(n) disk I/O per call, several times per
    # request). Now the file is read once and kept in a dict id -> Sismo;
    # each write still dumps the file so nothing is lost on restart.
    # Copies are returned so a service that fails half-way through a
    # validation never leaves a partially modified event in the cache.
    # ------------------------------------------------------------------

    def _cargar_cache(self) -> dict:
        if self._cache is None:
            self._cache = {}
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, list):
                    for item in raw_data:
                        try:
                            sismo = self._to_entity(item)
                            self._cache[sismo.id] = sismo
                        except (KeyError, ValueError, TypeError, IndexError):
                            continue
            except (OSError, json.JSONDecodeError):
                pass
        return self._cache

    @staticmethod
    def _copia(sismo: Sismo) -> Sismo:
        return replace(sismo, reporting_stations=set(sismo.reporting_stations))

    def _persistir(self) -> None:
        self._write_raw_data([self._to_dict(s) for s in self._cargar_cache().values()])

    def get_all(self) -> List[Sismo]:
        """Returns copies of all stored events."""
        return [self._copia(s) for s in self._cargar_cache().values()]

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """O(1) lookup by id."""
        sismo = self._cargar_cache().get(sismo_id)
        return self._copia(sismo) if sismo is not None else None

    def save(self, sismo: Sismo) -> Sismo:
        """Inserts or updates an event and writes the file."""
        self._cargar_cache()[sismo.id] = self._copia(sismo)
        self._persistir()
        return sismo

    def delete(self, sismo_id: int) -> bool:
        """Removes an event from the file."""
        if self._cargar_cache().pop(sismo_id, None) is None:
            return False
        self._persistir()
        return True

    def generate_next_id(self) -> int:
        """Next free numeric id (max + 1)."""
        cache = self._cargar_cache()
        return max(cache, default=0) + 1