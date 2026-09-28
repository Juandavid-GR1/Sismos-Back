from flask import Blueprint, jsonify, request
from src.Models.Estaciones import Station
from src.business.services.EstacionesService import (
    StationService,
    StationValidationError,
)
from src.dataaccess.repository.JsonStationRepository import JsonStationRepository

# Configuración del Blueprint
station_bp = Blueprint("stations", __name__, url_prefix="/estaciones")
station_bp.strict_slashes = False

# 1. Instancias el repositorio
repository = JsonStationRepository()

station_service = StationService(repository=repository)


def _station_to_dict(station: Station) -> dict:
    """Función auxiliar para serializar el objeto Station a JSON."""
    return {
        "id": station.id,
        "name": station.name,
        "lat": station.lat,
        "lon": station.lon,
        "status": station.status,
        "dept": station.dept,
        "coverage": station.coverage,
    }


# ==========================================
# MANEJADORES DE ERRORES GLOBALES
# ==========================================


@station_bp.errorhandler(StationValidationError)
def handle_validation_error(error: StationValidationError):
    """Captura errores de validación de negocio y devuelve HTTP 400."""
    return jsonify({"error": "Bad Request", "message": str(error)}), 400


@station_bp.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    """Manejador global para excepciones no controladas (HTTP 500)."""
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "Ocurrió un error inesperado en el servidor.",
            }
        ),
        500,
    )


# ==========================================
# RUTAS DE LA API (/estaciones)
# ==========================================


@station_bp.route("", methods=["GET"])
def get_all_stations():
    """Obtiene el listado completo de estaciones (GET /estaciones)."""
    stations = station_service.get_all()
    return jsonify([_station_to_dict(s) for s in stations]), 200


@station_bp.route("/cobertura", methods=["GET"])
def get_stations_in_coverage():
    """Busca estaciones que cubren un punto dado (GET /estaciones/cobertura?lat=X&lon=Y)."""
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if lat is None or lon is None:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Se requieren los parámetros de consulta 'lat' y 'lon'.",
                }
            ),
            400,
        )

    # Si implementaste el método en tu servicio, lo invoca de esta forma:
    stations = station_service.get_in_coverage(lat, lon)
    return jsonify([_station_to_dict(s) for s in stations]), 200


@station_bp.route("/<string:station_id>", methods=["GET"])
def get_station_by_id(station_id: str):
    """Obtiene una estación específica por su ID entero (GET /estaciones/<id>)."""
    station = station_service.get_by_id(station_id)
    if not station:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"La estación con ID '{station_id}' no fue encontrada.",
                }
            ),
            404,
        )

    return jsonify(_station_to_dict(station)), 200


@station_bp.route("", methods=["POST"])
def create_station():
    """Crea una o varias estaciones con ID entero autogenerado (POST /estaciones)."""
    data = request.get_json(silent=True)

    if data is None:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "El cuerpo de la petición debe ser un objeto o arreglo JSON válido.",
                }
            ),
            400,
        )

    result = station_service.create(data)

    if isinstance(result, list):
        return jsonify([_station_to_dict(s) for s in result]), 201

    return jsonify(_station_to_dict(result)), 201


@station_bp.route("/<string:station_id>", methods=["PUT"])
def update_station(station_id: str):
    """Actualiza una estación existente (PUT /estaciones/<id>)."""
    data = request.get_json(silent=True)

    if data is None:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "El cuerpo de la petición debe ser un objeto JSON válido.",
                }
            ),
            400,
        )

    updated_station = station_service.update(station_id, data)
    if not updated_station:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"La estación con ID '{station_id}' no fue encontrada para actualizar.",
                }
            ),
            404,
        )

    return jsonify(_station_to_dict(updated_station)), 200


@station_bp.route("/<string:station_id>", methods=["DELETE"])
def delete_station(station_id: str):
    """Elimina una estación por su ID (DELETE /estaciones/<id>)."""
    deleted = station_service.delete(station_id)
    if not deleted:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"La estación con ID '{station_id}' no fue encontrada para eliminar.",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "message": f"Estación '{station_id}' eliminada correctamente.",
                "status": "success",
            }
        ),
        200,
    )