import json
import os
from datetime import datetime
from typing import Any

from src.Models.Sismo import EstadoPersistencia, Sismo, StatusSismo
from src.Models.AccionSismo import AccionSismo


class HistorialAccionesRepository:
    """Persiste la pila de acciones deshacibles en orden de cima a base."""

    def __init__(self, json_file: str = "data/historial_acciones_sismos.json") -> None:
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        if not os.path.exists(self.json_file):
            self._write_raw([])

    def _write_raw(self, data: list[dict[str, Any]]) -> None:
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(data, archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    @staticmethod
    def _sismo_to_dict(sismo: Sismo) -> dict[str, Any]:
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
    def _sismo_from_dict(data: dict[str, Any]) -> Sismo:
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
            prioridad=(
                int(data["prioridad"])
                if data.get("prioridad") is not None else None
            ),
            clave=clave,
            reporting_stations=set(data.get("reporting_stations", [])),
            status=StatusSismo(data.get("status", StatusSismo.PENDIENTE.value)),
            estado_persistencia=EstadoPersistencia(
                data.get("estado_persistencia", EstadoPersistencia.ACTIVO.value)
            ),
        )

    def _action_to_dict(self, accion: AccionSismo) -> dict[str, Any]:
        return {
            "tipo": accion.tipo,
            "eventos": [self._sismo_to_dict(evento) for evento in accion.eventos],
            "ids_retirados_antes": sorted(accion.ids_retirados_antes),
            "metadatos": accion.metadatos,
        }

    def _action_from_dict(self, data: dict[str, Any]) -> AccionSismo:
        return AccionSismo(
            tipo=str(data["tipo"]),
            eventos=[
                self._sismo_from_dict(evento) for evento in data.get("eventos", [])
            ],
            ids_retirados_antes={
                int(identificador)
                for identificador in data.get("ids_retirados_antes", [])
            },
            metadatos=dict(data.get("metadatos", {})),
        )

    def cargar(self) -> list[AccionSismo]:
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if not isinstance(datos, list):
                return []
            return [
                self._action_from_dict(item)
                for item in datos
                if isinstance(item, dict)
            ]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    def guardar(self, acciones: list[AccionSismo]) -> None:
        self._write_raw([self._action_to_dict(accion) for accion in acciones])
