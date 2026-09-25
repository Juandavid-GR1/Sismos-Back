class PointInPolygon:

    @staticmethod
    def punto_en_polygon(
        longitud: float,
        latitud: float,
        polygon: list
    ) -> bool:
        """
        Determina si un punto está dentro de un polígono
        utilizando el algoritmo Ray Casting.
        """

        if not polygon:
            return False

        exterior = polygon[0]

        if len(exterior) < 3:
            return False

        dentro = False

        j = len(exterior) - 1

        for i in range(len(exterior)):

            xi, yi = exterior[i]
            xj, yj = exterior[j]

            intersecta = (
                ((yi > latitud) != (yj > latitud))
                and
                (
                    longitud
                    <
                    (xj - xi)
                    * (latitud - yi)
                    / (yj - yi)
                    + xi
                )
            )

            if intersecta:
                dentro = not dentro

            j = i

        return dentro