from src.Models.Sismo import Sismo, StatusSismo


class SismoFactory:

    @staticmethod
    def crear(
        sismo_id,
        magnitude,
        depth,
        epicenter_x,
        epicenter_y,
        timestamp
    ) -> Sismo:

        return Sismo(
            id=sismo_id,
            magnitude=magnitude,
            depth=depth,
            epicenter_x=epicenter_x,
            epicenter_y=epicenter_y,
            timestamp=timestamp,
            revision=0,
            prioridad=None,
            clave=None,
            reporting_stations=set(),
            status=StatusSismo.PENDIENTE
        )