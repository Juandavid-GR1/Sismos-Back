from dataclasses import dataclass


@dataclass
class Referencia:
    """
    Candidato a referencia de un sismo.

    Este modelo se utiliza para mostrar los sismos
    que cumplen los criterios de referencia.
    """

    id: int
    distancia: float
    magnitud: float

    def to_dict(self):
        return {
            "id": self.id,
            "distancia": self.distancia,
            "magnitud": self.magnitud,
        }