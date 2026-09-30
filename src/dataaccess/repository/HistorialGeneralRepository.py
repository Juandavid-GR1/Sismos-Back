import json
import os
from typing import Any


class HistorialGeneralRepository:
    """Persists the unified undo stack as JSON."""

    def __init__(self, json_file: str = "data/historial_acciones.json") -> None:
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        if not os.path.exists(self.json_file):
            self._write([])

    def _write(self, data: list[dict[str, Any]]) -> None:
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(data, archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    def cargar(self) -> list[dict[str, Any]]:
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                data = json.load(archivo)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def guardar(self, acciones: list[dict[str, Any]]) -> None:
        self._write(acciones)
