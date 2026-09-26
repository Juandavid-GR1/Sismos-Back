from typing import Any, Optional

from flask import Blueprint, jsonify, request
from flask.wrappers import Response

from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoService,
    SismoValidationError,
)
from src.dataaccess.repository.SismoJsonRepository import SismoJsonRepository
from src.Models.Sismo import Sismo

# ------------------------------------------------------------------------------
# Configuración & Inyección de Dependencias
# ------------------------------------------------------------------------------

sismo_bp = Blueprint("sismos", __name__, url_prefix="/sismos")
sismo_bp.strict_slashes = False

sismo_repo = SismoJsonRepository("sismos.json")
sismo_service = SismoService(repository=sismo_repo)

REQUIRED_EVENT_FIELDS = [
    "magnitude",
    "depth",
    "epicenter_x",
    "epicenter_y",
    "timestamp",
]


# ------------------------------------------------------------------------------
# Funciones Auxiliares
# ------------------------------------------------------------------------------

def _sismo_to_dict(sismo: Sismo) -> dict[str, Any]:
    """Serializa la entidad Sismo a un diccionario listo para ser devuelto en formato JSON.

    Args:
        sismo (Sismo): Entidad de dominio de sismo.

    Returns:
        dict[str, Any]: Diccionario serializado con las propiedades del sismo.
    """
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


def _validate_payload(
    data: Optional[dict[str, Any]], required_fields: list[str]
) -> Optional[tuple[Response, int]]:
    """Valida que la petición contenga un JSON estructurado y que no falten campos obligatorios.

    Args:
        data (Optional[dict[str, Any]]): Payload parseado de la petición HTTP.
        required_fields (list[str]): Lista de claves que deben estar presentes en el payload.

    Returns:
        Optional[tuple[Response, int]]: Respuesta JSON con error 400 en caso de fallo, o None si la validación es exitosa.
    """
    if not data:
        return jsonify({
            "error": "Bad Request",
            "message": "El cuerpo de la petición debe ser un objeto JSON válido.",
        }), 400

    missing = [field for field in required_fields if field not in data]

    if missing:
        return jsonify({
            "error": "Bad Request",
            "message": f"Faltan campos obligatorios: {', '.join(missing)}",
        }), 400

    return None


# ------------------------------------------------------------------------------
# Manejadores de Errores Globales
# ------------------------------------------------------------------------------

@sismo_bp.errorhandler(SismoValidationError)
def handle_validation_error(error: SismoValidationError) -> tuple[Response, int]:
    """Maneja las excepciones de validación del dominio retornando un error HTTP 400."""
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
    }), 400


@sismo_bp.errorhandler(SismoNotFoundError)
def handle_not_found_error(error: SismoNotFoundError) -> tuple[Response, int]:
    """Maneja las excepciones de recurso no encontrado retornando un error HTTP 404."""
    return jsonify({
        "error": "Not Found",
        "message": str(error),
    }), 404


# ------------------------------------------------------------------------------
# Rutas CRUD
# ------------------------------------------------------------------------------

@sismo_bp.route("", methods=["GET"])
def get_all_sismos() -> tuple[Response, int]:
    """Obtiene el listado completo de eventos sísmicos registrados.

    Returns:
        tuple[Response, int]: Lista de sismos serializados y código HTTP 200.
    """
    sismos = sismo_service.get_all()
    return jsonify([_sismo_to_dict(s) for s in sismos]), 200


@sismo_bp.route("", methods=["POST"])
def create_event() -> tuple[Response, int]:
    """Registra un nuevo evento sísmico en el sistema con estado PENDIENTE.

    Returns:
        tuple[Response, int]: Objeto del sismo creado y código HTTP 201.
    """
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
def get_sismo_by_id(sismo_id: int) -> tuple[Response, int]:
    """Consulta los datos de un evento sísmico por su identificador único.

    Args:
        sismo_id (int): Identificador numérico del sismo.

    Returns:
        tuple[Response, int]: Datos del sismo encontrado y código HTTP 200.
    """
    sismo = sismo_service.get_by_id(sismo_id)
    return jsonify(_sismo_to_dict(sismo)), 200


@sismo_bp.route("/<int:sismo_id>", methods=["PUT"])
def update_sismo(sismo_id: int) -> tuple[Response, int]:
    """Actualiza la información técnica de un evento existente.

    Si se detectan cambios en los parámetros físicos, la revisión
    se incrementa automáticamente desde la capa de servicio.

    Args:
        sismo_id (int): ID del sismo a actualizar.

    Returns:
        tuple[Response, int]: Mensaje de confirmación con el sismo actualizado y código HTTP 200.
    """
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
        "sismo": _sismo_to_dict(updated_sismo),
    }), 200


@sismo_bp.route("/<int:sismo_id>", methods=["DELETE"])
def delete_sismo(sismo_id: int) -> tuple[Response, int]:
    """Elimina permanentemente un evento sísmico del sistema.

    Args:
        sismo_id (int): ID del sismo a eliminar.

    Returns:
        tuple[Response, int]: Mensaje de eliminación exitosa y código HTTP 200.
    """
    sismo_service.delete(sismo_id)

    return jsonify({
        "message": f"Evento sísmico con ID {sismo_id} eliminado exitosamente.",
        "id": sismo_id,
    }), 200


# ------------------------------------------------------------------------------
# Rutas de Dominio / Reglas de Negocio
# ------------------------------------------------------------------------------

@sismo_bp.route("/<int:sismo_id>/consensus", methods=["POST"])
def add_consensus_report(sismo_id: int) -> tuple[Response, int]:
    """Añade una estación emisora para consenso sobre el evento sísmico.

    Args:
        sismo_id (int): ID del sismo sobre el cual se reporta consenso.

    Returns:
        tuple[Response, int]: Sismo actualizado con la nueva estación registrada y código HTTP 200.
    """
    data = request.get_json(silent=True)

    if not data or "station_id" not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Se requiere el campo 'station_id' en el cuerpo JSON.",
        }), 400

    updated_sismo = sismo_service.add_consensus_report(
        sismo_id=sismo_id,
        station_id=data["station_id"],
    )

    return jsonify(_sismo_to_dict(updated_sismo)), 200


@sismo_bp.route("/<int:sismo_id>/correction", methods=["PUT"])
def apply_correction(sismo_id: int) -> tuple[Response, int]:
    """Aplica una corrección física reportada por una estación sísmica.

    Requiere que la revisión enviada sea mayor a la revisión actual del evento.

    Args:
        sismo_id (int): ID del sismo a corregir.

    Returns:
        tuple[Response, int]: Sismo actualizado con la nueva revisión y código HTTP 200.
    """
    data = request.get_json(silent=True)

    if not data or "station_id" not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Se requiere el campo 'station_id' en el cuerpo JSON.",
        }), 400

    if "revision" not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Se requiere el campo 'revision' en el cuerpo JSON.",
        }), 400

    updated_sismo = sismo_service.apply_correction(
        sismo_id=sismo_id,
        station_id=data["station_id"],
        magnitude=data.get("magnitude"),
        depth=data.get("depth"),
        epicenter_x=data.get("epicenter_x"),
        epicenter_y=data.get("epicenter_y"),
        revision=data["revision"],
    )

    return jsonify(_sismo_to_dict(updated_sismo)), 200


@sismo_bp.route("/<int:sismo_id>/audit", methods=["PATCH"])
def audit_and_validate(sismo_id: int) -> tuple[Response, int]:
    """Audita el evento sísmico y actualiza su estado a REVISADO.

    Args:
        sismo_id (int): ID del sismo a auditar.

    Returns:
        tuple[Response, int]: Sismo actualizado con el estado REVISADO y código HTTP 200.
    """
    validated_sismo = sismo_service.audit_and_validate(sismo_id)

    return jsonify(_sismo_to_dict(validated_sismo)), 200