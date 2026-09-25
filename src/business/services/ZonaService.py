from src.dataaccess.repository.ZonaRepository import ZonaRepository
from src.business.algortimos.zonas.PointInPolygon import PointInPolygon


class ZonaService:
    """
    Servicio encargado de gestionar las zonas geográficas
    utilizadas por el sistema.
    """

    def __init__(
        self,
        repository: ZonaRepository
    ):
        self.repository = repository

    def get_all(self) -> dict:
        """
        Retorna todas las zonas en formato GeoJSON.
        """
        return self.repository.get_all()

    def punto_en_zona(
        self,
        longitud: float,
        latitud: float
    ) -> bool:
        """
        Determina si un punto se encuentra dentro
        de alguna zona poblada.
        """

        geojson = self.repository.get_all()

        features = geojson.get("features", [])

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            if properties.get("poblada") is not True:
                continue

            geometry = feature.get(
                "geometry",
                {}
            )

            geometry_type = geometry.get("type")
            coordinates = geometry.get(
                "coordinates",
                []
            )

            if geometry_type == "Polygon":

                if PointInPolygon.punto_en_polygon(
                    longitud,
                    latitud,
                    coordinates
                ):
                    return True

            elif geometry_type == "MultiPolygon":

                for polygon in coordinates:

                    if PointInPolygon.punto_en_polygon(
                        longitud,
                        latitud,
                        polygon
                    ):
                        return True

        return False