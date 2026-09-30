from datetime import datetime, timezone


class SismoComparison:
    """
    Consistent equality of the physical data of an event.
    """

    @staticmethod
    def decimas(valor) -> int:
        return int(round(float(valor) * 10))

    @staticmethod
    def normalizar_fecha(fecha: datetime | None) -> datetime | None:
        if fecha is None:
            return None
        if fecha.tzinfo is not None:
            fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
        return fecha.replace(microsecond=0)

    @staticmethod
    def millonesimas(valor) -> int:
        return int(round(float(valor) * 1_000_000))

    @classmethod
    def mismos_datos(cls, sismo, magnitude, depth, epicenter_x, epicenter_y, timestamp=None) -> bool:
        iguales = (
            cls.decimas(sismo.magnitude) == cls.decimas(magnitude)
            and cls.decimas(sismo.depth) == cls.decimas(depth)
            and cls.millonesimas(sismo.epicenter_x) == cls.millonesimas(epicenter_x)
            and cls.millonesimas(sismo.epicenter_y) == cls.millonesimas(epicenter_y)
        )
        if iguales and timestamp is not None:
            iguales = cls.normalizar_fecha(sismo.timestamp) == cls.normalizar_fecha(timestamp)
        return iguales

    @classmethod
    def tiene_cambios(cls, sismo, magnitude, depth, epicenter_x, epicenter_y, timestamp=None) -> bool:
        return not cls.mismos_datos(sismo, magnitude, depth, epicenter_x, epicenter_y, timestamp)