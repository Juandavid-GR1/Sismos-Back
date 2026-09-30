import json
import os
from dataclasses import replace
from datetime import datetime
from typing import Optional

from src.Models.Sismo import EstadoPersistencia, Sismo, StatusSismo


class HistorialSismosRepository:
    """Persistencia de eventos que ya no pertenecen al AVL activo."""

    def __init__(self, json_file: str = "data/historico_sismos.json") -> None:
        self.json_file = json_file
        self._cache: Optional[dict[int, Sismo]] = None
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.json_file):
            self._write_raw_data([])

    def _write_raw_data(self, data: list[dict]) -> None:
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(data, archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    @staticmethod
    def _to_dict(sismo: Sismo) -> dict:
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
            "reporting_stations": sorted(sismo.reporting_stations),
            "status": sismo.status.value,
            "estado_persistencia": sismo.estado_persistencia.value,
        }

    @staticmethod
    def _to_entity(data: dict) -> Sismo:
        clave_data = data.get("clave")
        clave = (
            (int(clave_data[0]), float(clave_data[1]), int(clave_data[2]))
            if clave_data is not None else None
        )
        return Sismo(
            id=int(data["id"]),
            magnitude=float(data["magnitude"]),
            depth=float(data["depth"]),
            epicenter_x=float(data["epicenter_x"]),
            epicenter_y=float(data["epicenter_y"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            revision=int(data.get("revision", 1)),
            prioridad=int(data["prioridad"]) if data.get("prioridad") is not None else None,
            clave=clave,
            reporting_stations=set(data.get("reporting_stations", [])),
            status=StatusSismo(data.get("status", StatusSismo.PENDIENTE.value)),
            estado_persistencia=EstadoPersistencia(
                data.get("estado_persistencia", EstadoPersistencia.ARCHIVADO.value)
            ),
        )

    @staticmethod
    def _copia(sismo: Sismo) -> Sismo:
        return replace(sismo, reporting_stations=set(sismo.reporting_stations))

    def _cargar_cache(self) -> dict[int, Sismo]:
        if self._cache is None:
            self._cache = {}
            try:
                with open(self.json_file, "r", encoding="utf-8") as archivo:
                    datos = json.load(archivo)
                if isinstance(datos, list):
                    for item in datos:
                        try:
                            sismo = self._to_entity(item)
                            self._cache[sismo.id] = sismo
                        except (KeyError, ValueError, TypeError, IndexError):
                            continue
            except (OSError, json.JSONDecodeError):
                pass
        return self._cache

    def _persistir(self) -> None:
        self._write_raw_data([
            self._to_dict(sismo) for sismo in self._cargar_cache().values()
        ])

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        sismo = self._cargar_cache().get(sismo_id)
        return self._copia(sismo) if sismo is not None else None

    def get_all(self) -> list[Sismo]:
        return [self._copia(sismo) for sismo in self._cargar_cache().values()]

    def save(self, sismo: Sismo) -> Sismo:
        if sismo.estado_persistencia == EstadoPersistencia.ACTIVO:
            raise ValueError("El histórico no puede almacenar eventos activos.")
        cache = self._cargar_cache()
        previo = cache.get(sismo.id)
        cache[sismo.id] = self._copia(sismo)
        try:
            self._persistir()
        except Exception:
            if previo is None:
                cache.pop(sismo.id, None)
            else:
                cache[sismo.id] = previo
            raise
        return sismo

    def delete(self, sismo_id: int) -> bool:
        if self._cargar_cache().pop(sismo_id, None) is None:
            return False
        self._persistir()
        return True

    def exportar(self) -> list[dict]:
        return [self._to_dict(sismo) for sismo in self._cargar_cache().values()]

    def reemplazar_todo(self, datos: list[dict]) -> None:
        self._cache = {}
        for item in datos:
            sismo = self._to_entity(item)
            self._cache[sismo.id] = sismo
        self._persistir()
