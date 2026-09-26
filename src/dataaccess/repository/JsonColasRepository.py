import json
import os
from datetime import datetime
from typing import Any

from src.business.interfaces.IF_Colas import ColaPersistencia
from src.Models.Reportes import Reporte


class ColaJsonPersistencia(ColaPersistencia):
    """Implementación de la interfaz de persistencia para la cola de reportes mediante almacenamiento en disco con JSON."""

    def __init__(self, ruta: str = "data/reportes_cola.json") -> None:
        """Inicializa el servicio de persistencia y garantiza la existencia de la estructura de archivos.

        Args:
            ruta (str, optional): Ruta relativa o absoluta del archivo JSON. Por defecto "data/reportes_cola.json".
        """
        self.ruta = ruta
        self._crear_archivo()

    def _crear_archivo(self) -> None:
        """Crea el directorio contenedor y un archivo JSON inicial con lista vacía si no existe."""
        carpeta = os.path.dirname(self.ruta)

        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        if not os.path.exists(self.ruta):
            with open(self.ruta, "w", encoding="utf-8") as archivo:
                json.dump([], archivo, ensure_ascii=False, indent=4)

    def guardar(self, reportes: list[Reporte]) -> None:
        """Persiste el listado de reportes serializados en el archivo JSON.

        Args:
            reportes (list[Reporte]): Colección de objetos Reporte a guardar.
        """
        datos = [self._reporte_a_dict(reporte) for reporte in reportes]

        with open(self.ruta, "w", encoding="utf-8") as archivo:
            json.dump(
                datos,
                archivo,
                ensure_ascii=False,
                indent=4,
            )

    def cargar(self) -> list[Reporte]:
        """Carga y deserializa los reportes almacenados en el archivo JSON.

        Returns:
            list[Reporte]: Lista de instancias de Reporte recovered de disco.
                           Devuelve lista vacía en caso de que no exista el archivo o el formato no sea válido.
        """
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            return [self._dict_a_reporte(data) for data in datos]

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _reporte_a_dict(self, reporte: Reporte) -> dict[str, Any]:
        """Convierte una entidad Reporte a un diccionario serializable a JSON.

        Args:
            reporte (Reporte): Entidad de modelo a serializar.

        Returns:
            dict[str, Any]: Diccionario con las propiedades del reporte.
        """
        return {
            "sismo_id": reporte.sismo_id,
            "station_id": reporte.station_id,
            "magnitude": reporte.magnitude,
            "depth": reporte.depth,
            "epicenter_x": reporte.epicenter_x,
            "epicenter_y": reporte.epicenter_y,
            "timestamp": reporte.timestamp.isoformat(),
            "revision": reporte.revision,
        }

    def _dict_a_reporte(self, data: dict[str, Any]) -> Reporte:
        """Reconstruye un objeto de dominio Reporte a partir de un diccionario deserializado.

        Args:
            data (dict[str, Any]): Diccionario con los datos del reporte.

        Returns:
            Reporte: Instancia del modelo Reporte.
        """
        return Reporte(
            sismo_id=data["sismo_id"],
            station_id=data["station_id"],
            magnitude=data["magnitude"],
            depth=data["depth"],
            epicenter_x=data["epicenter_x"],
            epicenter_y=data["epicenter_y"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            revision=data["revision"],
        )