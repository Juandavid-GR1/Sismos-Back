from typing import Any, Optional

from flask import Blueprint, jsonify, request
from flask.wrappers import Response

from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoService,
    SismoValidationError,
)
from src.Models.Sismo import Sismo

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
        "estado_persistencia": sismo.estado_persistencia.value,
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
# Registro de rutas 
# ------------------------------------------------------------------------------

def register_sismo_routes(app, sismo_service: SismoService):
    sismo_bp = Blueprint("sismos", __name__, url_prefix="/sismos")
    sismo_bp.strict_slashes = False

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

    # --------------------------------------------------------------------
    # Rutas CRUD
    # --------------------------------------------------------------------

    @sismo_bp.route("", methods=["GET"])
    def get_all_sismos() -> tuple[Response, int]:
        """Obtiene el listado completo de eventos sísmicos registrados."""
        sismos = sismo_service.get_all()
        return jsonify([_sismo_to_dict(s) for s in sismos]), 200

    @sismo_bp.route("", methods=["POST"])
    def create_event() -> tuple[Response, int]:
        """Registra un nuevo evento sísmico en el sistema con estado PENDIENTE."""
        data = request.get_json(silent=True)

        error_response = _validate_payload(data, REQUIRED_EVENT_FIELDS)
        if error_response:
            return error_response

        station_id = data.get("station_id") or data.get("initial_station_id")

        sismo_id = data.get("id", data.get("sismo_id"))
        if sismo_id in ("", None):
            sismo_id = None

        new_sismo = sismo_service.create_event(
            sismo_id=sismo_id,
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

        Sección 6 del enunciado: "El resultado debe indicar si está
        activo, archivado o eliminado. Para un evento activo se
        muestran sus datos vigentes... prioridad, clave, estado de
        atención, profundidad del nodo, altura, factor de balance y
        asociaciones."

        Nota: "archivado" todavía no existe en el sistema (depende de
        la sección 10, no construida) -- por ahora solo se distingue
        activo vs. eliminado. "asociaciones" tampoco existe todavía
        (sección 7) -- se omite ese campo por ahora.
        """
        try:
            sismo = sismo_service.get_by_id(sismo_id)
        except SismoNotFoundError:
            historico = sismo_service.get_historico_by_id(sismo_id)
            if historico is not None:
                datos = _sismo_to_dict(historico)
                datos["estado"] = historico.estado_persistencia.value
                return jsonify(datos), 200
            eliminados_service = getattr(sismo_service, "eliminados_service", None)
            if eliminados_service is not None and eliminados_service.esta_retirado(sismo_id):
                return jsonify({
                    "id": sismo_id,
                    "estado": "eliminado",
                    "mensaje": "Este identificador fue eliminado y está retirado.",
                }), 200
            raise

        datos = _sismo_to_dict(sismo)
        datos["estado"] = "activo"
        datos["estado_persistencia"] = sismo.estado_persistencia.value

        avl_service = getattr(sismo_service, "avl_service", None)
        if avl_service is not None:
            nodo = avl_service.buscar_por_id(sismo_id)
            if nodo is not None:
                arbol = avl_service.get_arbol()
                datos["profundidad_nodo"] = avl_service.profundidad_de(sismo_id)
                datos["altura_nodo"] = nodo.getAltura()
                datos["factor_balance"] = arbol._calcularFactorDeBalanceo(nodo)


        # ZonaService que ya calcula esto al crear/corregir eventos
        zona_service = getattr(sismo_service, "zona_service", None)
        if zona_service is not None:
            datos["zona_poblada"] = zona_service.punto_en_zona(
                longitud=sismo.epicenter_x,
                latitud=sismo.epicenter_y,
            )
        else:
            datos["zona_poblada"] = None

        # Pendiente: "asociaciones" (sección 7, no construida todavía)
        datos["asociaciones"] = None

        return jsonify(datos), 200

    @sismo_bp.route("/<int:sismo_id>", methods=["PUT", "PATCH"])
    def update_sismo(sismo_id: int) -> tuple[Response, int]:
        """Manual correction (section 6). The body may contain one or
        several of: magnitude, depth, epicenter_x, epicenter_y, timestamp.
        The id is immutable. Answers with the corrected event, its previous
        state and a report explaining what happened in the tree."""
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data:
            return jsonify({
                "error": "Bad Request",
                "message": "El cuerpo de la petición debe ser un objeto JSON con los datos a corregir.",
            }), 400

        resultado = sismo_service.corregir_evento(sismo_id, data)
        reporte = resultado["reporte"]

        return jsonify({
            "message": (
                f"Corrección aplicada: revisión {reporte['revision_anterior']} → "
                f"{reporte['revision_nueva']}. {reporte['explicacion']}"
            ),
            "sismo": _sismo_to_dict(resultado["sismo"]),
            "anterior": _sismo_to_dict(resultado["anterior"]),
            "correccion": reporte,
        }), 200

    @sismo_bp.route("/metricas", methods=["GET"])
    def metricas_sismos() -> tuple[Response, int]:
        """Accumulated event metrics (section 14)."""
        return jsonify(sismo_service.metricas()), 200

    @sismo_bp.route("/historico", methods=["GET"])
    def get_historico() -> tuple[Response, int]:
        """Obtiene eventos archivados o retirados."""
        return jsonify([_sismo_to_dict(sismo) for sismo in sismo_service.get_historico()]), 200

    @sismo_bp.route("/<int:sismo_id>/archivar", methods=["POST"])
    def archive_sismo_branch(sismo_id: int) -> tuple[Response, int]:
        """Archives the complete AVL subtree rooted at an event."""
        return jsonify(sismo_service.archivar_rama(sismo_id)), 200

    @sismo_bp.route("/<int:sismo_id>", methods=["DELETE"])
    def delete_sismo(sismo_id: int) -> tuple[Response, int]:
        """Elimina individualmente un evento y registra la acción."""
        if not sismo_service.delete(sismo_id):
            return jsonify({
                "error": "Not Found",
                "message": f"No se encontró el evento sísmico con ID {sismo_id}.",
            }), 404

        return jsonify({
            "message": f"Evento sísmico con ID {sismo_id} eliminado exitosamente.",
            "id": sismo_id,
        }), 200

    # --------------------------------------------------------------------
    # Rutas de Dominio / Reglas de Negocio
    # --------------------------------------------------------------------

    @sismo_bp.route("/<int:sismo_id>/consensus", methods=["POST"])
    def add_consensus_report(sismo_id: int) -> tuple[Response, int]:
        """Añade una estación emisora para consenso sobre el evento sísmico."""
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
        """Aplica una corrección física reportada por una estación sísmica."""
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
        """Audita el evento sísmico y actualiza su estado a REVISADO."""
        validated_sismo = sismo_service.audit_and_validate(sismo_id)

        return jsonify(_sismo_to_dict(validated_sismo)), 200

    app.register_blueprint(sismo_bp)