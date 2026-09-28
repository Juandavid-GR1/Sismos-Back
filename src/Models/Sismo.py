"""
Módulo del Modelo de Dominio: Sismo

Define la estructura de datos pura de la entidad Sismo, documentando
su ciclo de vida, trazabilidad por estaciones y mecanismo de revisión.

Mecanismo de Revisión y Consenso:

----------------------------------

1. Alta Inicial (Revisión 0):

   Al registrar inicialmente un evento sísmico, el sistema le asigna
   revision = 0.

   En este momento el sismo todavía no ha sido reportado por ninguna
   estación, por lo que reporting_stations permanece vacío y el estado
   se establece en PENDIENTE.

2. Reporte de una Estación:

   Cuando una estación reporta un sismo existente, el reporte es
   procesado por el sistema.

   La estación se agrega al conjunto reporting_stations y la revisión
   aumenta en una unidad.

3. Consenso entre Estaciones:

   Si otra estación reporta el mismo evento sin modificar las mediciones,
   se agrega su identificador al conjunto reporting_stations.

   La revisión aumenta porque se procesó un nuevo reporte, aunque los
   parámetros físicos del sismo permanezcan iguales.

4. Corrección de Datos:

   Si un reporte modifica alguno de los parámetros físicos del sismo
   (magnitud, profundidad o epicentro), se actualizan los datos.

   La estación reportante se agrega al conjunto reporting_stations,
   la revisión aumenta en una unidad y el estado vuelve a PENDIENTE.

5. Auditoría y Validación:

   Un operador o proceso de validación puede cambiar el estado del
   sismo a REVISADO.

   Si posteriormente se procesa una nueva corrección, el estado vuelve
   a PENDIENTE.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StatusSismo(str, Enum):
    """
    Representa los estados de atención posibles para un evento sísmico.

    Atributos:
        PENDIENTE (str):
            Estado asignado al crear el evento o al aplicar una corrección.

        REVISADO (str):
            Estado asignado tras auditar y aprobar la revisión vigente.
    """

    PENDIENTE = "Pendiente"
    REVISADO = "Revisado"


@dataclass
class Sismo:
    """
    Entidad que representa un evento sísmico con control de revisiones
    y procedencia por estaciones.

    Atributos:

        id (int):
            Identificador entero único (entre 1 y 999999).

            Se utiliza exclusivamente como identificador numérico
            del evento.

        magnitude (float):
            Magnitud M (-2.0 a 10.0) con máximo un decimal.

        depth (float):
            Profundidad H del hipocentro en kilómetros
            (0.0 a 700.0) con máximo un decimal.

        epicenter_x (float):
            Longitud geográfica del epicentro
            (-180.0 a 180.0 grados).

        epicenter_y (float):
            Latitud geográfica del epicentro
            (-90.0 a 90.0 grados).

        timestamp (datetime):
            Instante de ocurrencia del evento sísmico.

        revision (int, opcional):
            Número de revisión del evento.

            Un sismo recién creado comienza en revisión 0.
            Cada reporte procesado incrementa la revisión en una unidad.

        reporting_stations (set[str], opcional):
            Conjunto de estaciones cuyos reportes han sido procesados
            para este sismo.

            Se utiliza un conjunto para evitar duplicar una misma
            estación.

        status (StatusSismo, opcional):
            Estado actual de atención del evento.

            Inicia en PENDIENTE y vuelve a PENDIENTE cuando se acepta
            una corrección.
    """

    # ------------------------------------------------------------------
    # Identificador del sismo
    # ------------------------------------------------------------------

    id: int

    # ------------------------------------------------------------------
    # Parámetros físicos del evento sísmico
    # ------------------------------------------------------------------

    magnitude: float
    depth: float

    # Coordenadas geográficas mundiales
    # epicenter_x -> longitud
    # epicenter_y -> latitud

    epicenter_x: float
    epicenter_y: float

    # ------------------------------------------------------------------
    # Fecha y hora del evento
    # ------------------------------------------------------------------

    timestamp: datetime

    # ------------------------------------------------------------------
    # Control de revisión
    #
    # Un sismo nuevo comienza en revisión 0 porque todavía no ha sido
    # procesado ningún reporte de estación.
    # ------------------------------------------------------------------

    revision: int = 1



    prioridad: int | None = None
    clave: tuple[int, float, int] | None = None
    # ------------------------------------------------------------------
    # Estaciones que han reportado el sismo
    #
    # Se utiliza set para evitar estaciones duplicadas.
    # ------------------------------------------------------------------

    reporting_stations: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------
    # Estado actual del sismo
    # ------------------------------------------------------------------

    status: StatusSismo = StatusSismo.PENDIENTE

    # ------------------------------------------------------------------
    # PROPIEDADES
    # ------------------------------------------------------------------

    @property
    def formatted_id(self) -> str:
        """
        Retorna la representación textual formateada del ID del sismo.

        Returns:
            str:
                Cadena con el formato 'SIS-XXXXXX'.
        """

        return f"SIS-{self.id:06d}"

    @property
    def epicenter(self) -> tuple[float, float]:
        """
        Retorna las coordenadas geográficas del epicentro como
        un par ordenado.

        Returns:
            tuple[float, float]:
                Tupla (longitud, latitud).

                epicenter_x -> longitud (-180.0 a 180.0)
                epicenter_y -> latitud (-90.0 a 90.0)
        """

        return (self.epicenter_x, self.epicenter_y)