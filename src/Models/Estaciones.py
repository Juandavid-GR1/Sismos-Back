class Station:
    """Modelo de la entidad Station con sus atributos y constructor."""

    def __init__(
        self,
        name: str,
        lat: float,
        lon: float,
        status: str,
        dept: str,
        coverage: float,
        id: str | None = None,
    ):
        self.id = id
        self.name = name
        self.lat = lat
        self.lon = lon
        self.status = status
        self.dept = dept
        self.coverage = coverage  # Rango de visión/cobertura (ej: en km)