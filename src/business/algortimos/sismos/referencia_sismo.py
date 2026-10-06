from datetime import timezone
from math import radians, sin, cos, sqrt, atan2

from src.Models.Referencia import Referencia


# Ventana máxima de tiempo para considerar un sismo
# como posible referencia.
VENTANA_HORAS = 48

# Distancia máxima permitida entre los epicentros,
# expresada en kilómetros.
RADIO_KM = 40

def _en_utc(fecha):
    """Compara fechas en UTC: unas llegan con zona horaria ("Z") y otras sin ella."""
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)

def calcular_distancia(x1, y1, x2, y2):
    """
    Calcula la distancia geográfica entre dos puntos
    utilizando la fórmula de Haversine.

    Las coordenadas representan:

        x = longitud
        y = latitud

    Parámetros:
        x1: Longitud del primer punto.
        y1: Latitud del primer punto.
        x2: Longitud del segundo punto.
        y2: Latitud del segundo punto.

    Retorna:
        float: Distancia entre los dos puntos en kilómetros.
    """

    # Radio aproximado de la Tierra en kilómetros.
    R = 6371.0

    # Conversión de grados a radianes.
    longitud1 = radians(x1)
    latitud1 = radians(y1)

    longitud2 = radians(x2)
    latitud2 = radians(y2)

    # Diferencias entre las coordenadas.
    diferencia_longitud = longitud2 - longitud1
    diferencia_latitud = latitud2 - latitud1

    # Fórmula de Haversine.
    a = (
        sin(diferencia_latitud / 2) ** 2
        +
        cos(latitud1)
        * cos(latitud2)
        * sin(diferencia_longitud / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    # Distancia final en kilómetros.
    return R * c


def es_referencia_candidata(
    evento_a,
    evento_b,
    ventana_horas=VENTANA_HORAS,
    radio_km=RADIO_KM,
):
    """
    Determina si un sismo puede ser utilizado como
    referencia de otro sismo.

    Para que evento_a sea una referencia válida de
    evento_b debe cumplir todos los siguientes criterios:

    1. No puede ser el mismo sismo.
    2. Debe tener una magnitud estrictamente mayor.
    3. Debe haber ocurrido antes.
    4. La diferencia temporal debe ser como máximo
       de 48 horas.
    5. La distancia entre los epicentros debe ser
       como máximo de 40 kilómetros.

    Parámetros:
        evento_a: Sismo candidato a referencia.
        evento_b: Sismo que está siendo analizado.

    Retorna:
        bool: True si el candidato cumple todos los
        criterios; False en caso contrario.
    """

    # -------------------------------------------------
    # 1. No comparar el sismo consigo mismo
    # -------------------------------------------------

    if evento_a.id == evento_b.id:
        return False

    # -------------------------------------------------
    # 2. La referencia debe tener mayor magnitud
    # -------------------------------------------------

    if evento_a.magnitude <= evento_b.magnitude:
        return False

    # -------------------------------------------------
    # 3. La referencia debe haber ocurrido antes
    # -------------------------------------------------

    if _en_utc(evento_a.timestamp) >= _en_utc(evento_b.timestamp):
        return False

    # -------------------------------------------------
    # 4. Ventana temporal
    # -------------------------------------------------

    diferencia_horas = (
        _en_utc(evento_b.timestamp) - _en_utc(evento_a.timestamp)
    ).total_seconds() / 3600

    if diferencia_horas > ventana_horas:
        return False

    # -------------------------------------------------
    # 5. Distancia entre epicentros
    # -------------------------------------------------

    distancia = calcular_distancia(
        evento_a.epicenter_x,
        evento_a.epicenter_y,
        evento_b.epicenter_x,
        evento_b.epicenter_y
    )

    if distancia > radio_km:
        return False

    # Si supera todos los criterios, es una referencia válida.
    return True


def crear_referencia(evento_a, evento_b):
    """
    Crea una instancia de Referencia a partir de dos sismos.

    La distancia almacenada corresponde a la distancia
    geográfica entre sus epicentros y está expresada
    en kilómetros.

    Parámetros:
        evento_a: Sismo que será utilizado como referencia.
        evento_b: Sismo al cual pertenece la referencia.

    Retorna:
        Referencia: Objeto con el identificador, distancia
        y magnitud del sismo de referencia.
    """

    distancia = calcular_distancia(
        evento_a.epicenter_x,
        evento_a.epicenter_y,
        evento_b.epicenter_x,
        evento_b.epicenter_y
    )

    return Referencia(
        id=evento_a.id,
        distancia=distancia,
        magnitud=evento_a.magnitude
    )