from flask import Blueprint, jsonify, request

from src.Models.Sismo import Sismo
from src.dataaccess.repository.SismoJsonRepository import SismoJsonRepository
from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoService,
    SismoValidationError,
)

# ------------------------------------------------------------------------------
# Configuración & Inyección de Dependencias
# ------------------------------------------------------------------------------

sismo_bp = Blueprint("sismos", __name__, url_prefix="/sismos")
sismo_bp.strict_slashes = False

sismo_repo = SismoJsonRepository("sismos.json")
sismo_service = SismoService(repository=sismo_repo)

REQUIRED_EVENT_FIELDS = ["magnitude", "depth", "epicenter_x", "epicenter_y", "timestamp"]


# ------------------------------------------------------------------------------
# Funciones Auxiliares
# ------------------------------------------------------------------------------

def _sismo_to_dict(sismo: Sismo) -> dict:
    """Serializa la entidad Sismo a un diccionario listo para la respuesta JSON."""
    return {
        "id": sismo.id,
        "formatted_id": sismo.formatted_id,
        "magnitude": sismo.magnitude,
        "depth": sismo.depth,
        "epicenter_x": sismo.epicenter_x,
        "epicenter_y": sismo.epicenter_y,
        "epicenter": sismo.epicenter,
        "timestamp": sismo.timestamp.isoformat(),
        "revision": sismo.revision,
        "reporting_stations": list(sismo.reporting_stations),
        "status": sismo.status.value,
        "prioridad": sismo.prioridad,
        "clave": list(sismo.clave) if sismo.clave is not None else None,
    }


def _validate_payload(data: dict, required_fields: list[str]):
    """Valida la presencia del cuerpo JSON y de los campos obligatorios."""
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "El cuerpo de la petición debe ser un objeto JSON válido."
        }), 400

    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({
            "error": "Bad Request",
            "message": f"Faltan campos obligatorios: {', '.join(missing)}"
        }), 400

    return None


# ------------------------------------------------------------------------------
# Manejadores de Errores Globales
# ------------------------------------------------------------------------------

@sismo_bp.errorhandler(SismoValidationError)
def handle_validation_error(error: SismoValidationError):
    return jsonify({"error": "Bad Request", "message": str(error)}), 400


@sismo_bp.errorhandler(SismoNotFoundError)
def handle_not_found_error(error: SismoNotFoundError):
    return jsonify({"error": "Not Found", "message": str(error)}), 404


# ------------------------------------------------------------------------------
# Rutas CRUD
# ------------------------------------------------------------------------------

@sismo_bp.route("", methods=["GET"])
def get_all_sismos():
    """Obtiene la lista completa de eventos sísmicos."""
    sismos = sismo_service.get_all()
    return jsonify([_sismo_to_dict(s) for s in sismos]), 200


@sismo_bp.route("", methods=["POST"])
def create_event():
    """Alta inicial de un evento sísmico (Estado: PENDIENTE)."""
    data = request.get_json(silent=True)
    error_response = _validate_payload(data, REQUIRED_EVENT_FIELDS)
    if error_response:
        return error_response

    station_id = data.get("station_id") or data.get("initial_station_id")

    new_sismo = sismo_service.create_event(
        magnitude=data["magnitude"],
        depth=data["depth"],
        epicenter_x=data["epicenter_x"],
        epicenter_y=data["epicenter_y"],
        timestamp=data["timestamp"],
        initial_station_id=station_id,
    )
    return jsonify(_sismo_to_dict(new_sismo)), 201


@sismo_bp.route("/<int:sismo_id>", methods=["GET"])
def get_sismo_by_id(sismo_id: int):
    """Obtiene un evento sísmico específico por su ID."""
    sismo = sismo_service.get_by_id(sismo_id)
    return jsonify(_sismo_to_dict(sismo)), 200


@sismo_bp.route("/<int:sismo_id>", methods=["PUT"])
def update_sismo(sismo_id: int):
    """Actualiza la información técnica de un evento desde el sistema de edición."""
    data = request.get_json(silent=True)
    error_response = _validate_payload(data, REQUIRED_EVENT_FIELDS)
    if error_response:
        return error_response

    updated_sismo = sismo_service.update_event(
        sismo_id=sismo_id,
        magnitude=data["magnitude"],
        depth=data["depth"],
        epicenter_x=data["epicenter_x"],
        epicenter_y=data["epicenter_y"],
        timestamp=data["timestamp"],
    )

    return jsonify({
        "message": "Sismo actualizado correctamente.",
        "sismo": _sismo_to_dict(updated_sismo)
    }), 200


@sismo_bp.route("/<int:sismo_id>", methods=["DELETE"])
def delete_sismo(sismo_id: int):
    """Elimina un evento sísmico por su ID."""
    sismo_service.delete(sismo_id)
    return jsonify({
        "message": f"Evento sísmico con ID {sismo_id} eliminado exitosamente.",
        "id": sismo_id
    }), 200


# ------------------------------------------------------------------------------
# Rutas de Dominio / Reglas de Negocio
# ------------------------------------------------------------------------------

@sismo_bp.route("/<int:sismo_id>/consensus", methods=["POST"])
def add_consensus_report(sismo_id: int):
    """Regla 2: Agrega una estación emisora para consenso."""
    data = request.get_json(silent=True)
    if not data or "station_id" not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Se requiere el campo 'station_id' en el cuerpo JSON."
        }), 400

    updated_sismo = sismo_service.add_consensus_report(
        sismo_id=sismo_id,
        station_id=data["station_id"]
    )
    return jsonify(_sismo_to_dict(updated_sismo)), 200


@sismo_bp.route("/<int:sismo_id>/correction", methods=["PUT"])
def apply_correction(sismo_id: int):
    """Regla 3: Aplica una corrección proveniente de una estación sísmica."""
    data = request.get_json(silent=True)
    if not data or "station_id" not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Se requiere el campo 'station_id' en el cuerpo JSON."
        }), 400

    updated_sismo = sismo_service.apply_correction(
        sismo_id=sismo_id,
        station_id=data["station_id"],
        magnitude=data.get("magnitude"),
        depth=data.get("depth"),
        epicenter_x=data.get("epicenter_x"),
        epicenter_y=data.get("epicenter_y"),
    )
    return jsonify(_sismo_to_dict(updated_sismo)), 200


@sismo_bp.route("/<int:sismo_id>/audit", methods=["PATCH"])
def audit_and_validate(sismo_id: int):
    """Regla 4: Cambia el estado del evento a REVISADO."""
    validated_sismo = sismo_service.audit_and_validate(sismo_id)
    return jsonify(_sismo_to_dict(validated_sismo)), 200