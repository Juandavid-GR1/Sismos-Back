import json
from pathlib import Path


class ZonaRepository:
    """
    Repository encargado de leer las zonas geográficas
    almacenadas en un archivo GeoJSON.
    """

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)

    def get_all(self) -> dict:
        """
        Retorna todas las zonas almacenadas en el archivo GeoJSON.
        """

        if not self.json_path.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo de zonas: {self.json_path}"
            )

        with self.json_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)