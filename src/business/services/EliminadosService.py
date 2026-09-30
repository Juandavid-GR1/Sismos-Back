"""
Registro persistente de identificadores retirados.

Los IDs retirados se conservan entre reinicios y bloquean nuevos reportes
hasta que una futura acción de deshacer los quite explícitamente.
"""

import json
import os
from typing import Iterable
class EliminadosService:

    def __init__(self, json_file: str = "retirados.json"):
        self.json_file = json_file
        self._retirados = self._cargar()

    def _cargar(self) -> set[int]:
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            return {int(identificador) for identificador in datos}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return set()

    def _persistir(self) -> None:
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(sorted(self._retirados), archivo, indent=2)
        os.replace(temporal, self.json_file)

    def marcar_retirado(self, sismo_id: int) -> None:
        self._retirados.add(sismo_id)
        self._persistir()

    def desmarcar_retirado(self, sismo_id: int) -> None:
        self._retirados.discard(sismo_id)
        self._persistir()

    def cargar_ids(self, identificadores: Iterable[int]) -> None:
        self._retirados = {int(identificador) for identificador in identificadores}
        self._persistir()

    def esta_retirado(self, sismo_id: int) -> bool:
        return sismo_id in self._retirados

    def todos(self) -> set:
        """Copia del conjunto completo -- para exportación futura."""
        return set(self._retirados)

    def cantidad(self) -> int:
        return len(self._retirados)