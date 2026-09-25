class PriorityKeyService:

    @staticmethod
    def calcular_prioridad(
        magnitude: float,
        depth: float,
        zona_poblada: bool
    ) -> int:

        if (
            magnitude >= 6.0
            or (
                magnitude >= 4.5
                and depth <= 30.0
                and zona_poblada
            )
        ):
            return 3

        if magnitude >= 4.5:
            return 2

        return 1

    @staticmethod
    def generar_clave(
        prioridad: int,
        magnitude: float,
        sismo_id: int
    ) -> tuple[int, float, int]:

        return (
            prioridad,
            magnitude,
            sismo_id
        )