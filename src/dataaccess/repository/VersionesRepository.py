import copy
import json
import os
from datetime import datetime


class VersionesRepository:
    """Persistent named snapshots, intentionally independent from undo history."""

    def __init__(self, json_file: str = "data/versiones.json"):
        self.json_file = json_file
        self._versiones = {}
        self._cargar()

    def _cargar(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if isinstance(datos, dict):
                self._versiones = datos
        except (OSError, json.JSONDecodeError, TypeError):
            self._versiones = {}

    def _persistir(self):
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(self._versiones, archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    def guardar(self, nombre: str, estado: dict) -> dict:
        ahora = datetime.now().isoformat()
        self._versiones[nombre] = {
            "nombre": nombre,
            "fecha": ahora,
            "estado": copy.deepcopy(estado),
        }
        self._persistir()
        return {"nombre": nombre, "fecha": ahora}

    def listar(self) -> list[dict]:
        return [
            {"nombre": item["nombre"], "fecha": item["fecha"]}
            for item in sorted(
                self._versiones.values(), key=lambda item: item["nombre"]
            )
        ]

    def obtener(self, nombre: str) -> dict | None:
        item = self._versiones.get(nombre)
        return copy.deepcopy(item) if item is not None else None

    def eliminar(self, nombre: str) -> bool:
        if nombre not in self._versiones:
            return False
        del self._versiones[nombre]
        self._persistir()
        return True
