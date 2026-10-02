import json
import os
from datetime import datetime

from src.Models.ReferenciaSismo import ReferenciaSismo


class ReferenciaSismoRepository:
    """Persistent storage for the selected event references and settings."""

    def __init__(self, json_file: str = "data/referencias_sismo.json"):
        self.json_file = json_file
        self.referencias: dict[int, ReferenciaSismo] = {}
        self.ventana_horas = 48.0
        self.radio_km = 40.0
        self._cargar()

    def _cargar(self) -> None:
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError, TypeError):
            return

        if isinstance(datos, list):
            items = datos
        elif isinstance(datos, dict):
            items = datos.get("referencias", [])
            self.ventana_horas = float(datos.get("ventana_horas", 48))
            self.radio_km = float(datos.get("radio_km", 40))
        else:
            return

        for item in items:
            try:
                referencia = ReferenciaSismo(
                    sismo_id=int(item["sismo_id"]),
                    referencia_id=int(item["referencia_id"]),
                    distancia=float(item["distancia"]),
                    fecha_creacion=datetime.fromisoformat(item["fecha_creacion"]),
                )
                self.referencias[referencia.sismo_id] = referencia
            except (KeyError, TypeError, ValueError):
                continue

    def _persistir(self) -> None:
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        datos = {
            "ventana_horas": self.ventana_horas,
            "radio_km": self.radio_km,
            "referencias": [
                referencia.to_dict()
                for referencia in sorted(self.referencias.values(), key=lambda item: item.sismo_id)
            ],
        }
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    def guardar(self, referencia: ReferenciaSismo) -> ReferenciaSismo:
        self.referencias[referencia.sismo_id] = referencia
        self._persistir()
        return referencia

    def obtener_por_sismo(self, sismo_id: int) -> ReferenciaSismo | None:
        return self.referencias.get(sismo_id)

    def eliminar_por_sismo(self, sismo_id: int) -> bool:
        if self.referencias.pop(sismo_id, None) is None:
            return False
        self._persistir()
        return True

    def todos(self) -> list[ReferenciaSismo]:
        return list(self.referencias.values())

    def exportar(self) -> dict:
        return {
            "ventana_horas": self.ventana_horas,
            "radio_km": self.radio_km,
            "referencias": [
                referencia.to_dict()
                for referencia in self.todos()
            ],
        }

    def reemplazar_todo(self, estado: dict | list) -> None:
        self.referencias.clear()
        if isinstance(estado, list):
            estado = {"referencias": estado}
        self.ventana_horas = float(estado.get("ventana_horas", 48))
        self.radio_km = float(estado.get("radio_km", 40))
        for item in estado.get("referencias", []):
            referencia = ReferenciaSismo(
                sismo_id=int(item["sismo_id"]),
                referencia_id=int(item["referencia_id"]),
                distancia=float(item["distancia"]),
                fecha_creacion=datetime.fromisoformat(item["fecha_creacion"]),
            )
            self.referencias[referencia.sismo_id] = referencia
        self._persistir()

    def configurar(self, ventana_horas: float, radio_km: float) -> None:
        self.ventana_horas = ventana_horas
        self.radio_km = radio_km
        self._persistir()
