"""
Módulo del Modelo de Dominio: Sismo

Define la estructura de datos pura de la entidad Sismo, documentando
su ciclo de vida, trazabilidad por estaciones y mecanismo de revisión.

Mecanismo de Revisión y Consenso:
----------------------------------
1. Alta Inicial (Revisión 1):
   Al registrar la primera notificación de un evento, el sistema le asigna
   `revision = 1`, almacena la estación emisora en `reporting_stations`
   y establece el estado en `PENDIENTE`.

2. Consenso entre Estaciones (Misma Revisión):
   Si otras estaciones confirman el mismo evento sin modificar las mediciones,
   sus identificadores se agregan al conjunto `reporting_stations`. La revisión
   y el estado no sufren alteraciones.

3. Corrección de Datos (Incremento de Revisión):
   Cualquier corrección aceptada en los parámetros físicos (magnitud, profundidad,
   o epicentro) incrementa el número de revisión (`revision + 1`) y retorna
   automáticamente el estado a `PENDIENTE` para nueva auditoría.

4. Auditoría y Validación:
   Un operador o proceso de validación cambia el estado a `REVISADO`. El ciclo
   se repite si ingresan nuevas correcciones.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StatusSismo(str, Enum):
    """
    Representa los estados de atención posibles para un evento sísmico.

    Atributos:
        PENDIENTE (str): Estado asignado al crear el evento o al aplicar una corrección.
        REVISADO (str): Estado asignado tras auditar y aprobar la revisión vigente.
    """

    PENDIENTE = "Pendiente"
    REVISADO = "Revisado"


@dataclass
class Sismo:
    """
    Entidad que representa un evento sísmico con control de revisiones y procedencia.

    Atributos:
        id (int): 
            Identificador entero único (entre 1 y 999999). 
            Inmutable y se compara exclusivamente por valor numérico.
            
        magnitude (float): 
            Magnitud M (-2.0 a 10.0) con máximo un decimal. 
            Escala global unificada dentro del simulador.
            
        depth (float): 
            Profundidad H del hipocentro en km (0.0 a 700.0) con máximo un decimal.
            
        epicenter_x (float): 
            Coordenada X del epicentro en km (0.0 a 1000.0) con máximo un decimal.
            
        epicenter_y (float): 
            Coordenada Y del epicentro en km (0.0 a 1000.0) con máximo un decimal.
            
        timestamp (datetime): 
            Instante de ocurrencia en UTC con precisión de segundos (ISO 8601).
            
        revision (int, opcional): 
            Número entero positivo (>= 1). Incrementa (+1) cada vez que se acepta
            una corrección sobre las mediciones. Por defecto inicia en 1.
            
        reporting_stations (set[str], opcional): 
            Conjunto de estaciones cuyos reportes han sido aceptados para esta revisión.
            Garantiza la trazabilidad del consenso entre estaciones.
            
        status (StatusSismo, opcional): 
            Estado de atención actual. Inicia en PENDIENTE y regresa a PENDIENTE
            ante cualquier incremento de revisión.
    """

    # Identificador numérico único e inmutable
    id: int

    # Parámetros físicos del evento sísmico
    magnitude: float
    depth: float
    epicenter_x: float
    epicenter_y: float
    timestamp: datetime

    # Control de versión, consenso de estaciones y estado de atención
    revision: int = 1
    reporting_stations: set[str] = field(default_factory=set)
    status: StatusSismo = StatusSismo.PENDIENTE

    @property
    def formatted_id(self) -> str:
        """
        Retorna la representación textual formateada del ID del sismo.

        Returns:
            str: Cadena con el formato 'SIS-XXXXXX' (ej: 'SIS-000010').
        """
        return f"SIS-{self.id:06d}"

    @property
    def epicenter(self) -> tuple[float, float]:
        """
        Retorna las coordenadas del epicentro como un par ordenado.

        Returns:
            tuple[float, float]: Tupla (epicenter_x, epicenter_y) en km.
        """
        return (self.epicenter_x, self.epicenter_y)