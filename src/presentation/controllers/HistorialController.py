from flask import Blueprint, g, jsonify, request

from src.business.services.HistorialService import EstadoService, HistorialService

METODOS_QUE_MODIFICAN = {"POST", "PUT", "PATCH", "DELETE"}
PREFIJOS_EXCLUIDOS = (
    "/historial",
    "/estaciones",
    "/sismos/acciones/deshacer",
)


def _sis(valor):
    try:
        return f"SIS-{int(valor):06d}"
    except (TypeError, ValueError):
        return "evento"


def describir_accion(endpoint: str, vista: dict, cuerpo: dict, respuesta: dict) -> str:
    """Short human description of the action for the history panel."""
    sid = vista.get("sismo_id") or (respuesta or {}).get("id") or (cuerpo or {}).get("id")
    reporte = (respuesta or {}).get("reporte") or {}
    decision = (respuesta or {}).get("decision")

    textos = {
        "sismos.create_event": lambda: f"Alta de {_sis(sid)}",
        "sismos.update_sismo": lambda: f"Corrección de {_sis(sid)}",
        "sismos.delete_sismo": lambda: f"Eliminación de {_sis(sid)}",
        "sismos.audit_and_validate": lambda: f"{_sis(sid)} marcado como revisado",
        "sismos.add_consensus_report": lambda: f"Confirmación de {_sis(sid)}",
        "sismos.apply_correction": lambda: f"Corrección por estación de {_sis(sid)}",
        "reporte_controller.crear_reporte": lambda: (
            f"Reporte encolado ({_sis((cuerpo or {}).get('sismo_id'))}, "
            f"estación {(cuerpo or {}).get('station_id')}, rev. {(cuerpo or {}).get('revision')})"
        ),
        "reporte_controller.validar_y_emitir": lambda: (
            f"Paso de cola: {decision or 'procesado'} ({_sis(reporte.get('sismo_id'))})"
        ),
        "reporte_controller.procesar_automaticamente": lambda: (
            f"Paso de cola: {decision or 'procesado'} ({_sis(reporte.get('sismo_id'))})"
        ),
        "reporte_controller.descartar_ruido": lambda: (
            f"Reporte descartado como ruido ({_sis(reporte.get('sismo_id'))})"
        ),
        "arbol.modo_estres": lambda: (
            "Modo estrés activado" if (cuerpo or {}).get("activo") else "Modo estrés desactivado"
        ),
        "arbol.recuperar_balance": lambda: "Recuperación global del balance",
        "reloj.avanzar_reloj": lambda: "Avance del reloj de simulación",
    }
    generar = textos.get(endpoint)
    return generar() if generar else f"{request.method} {request.path}"


def register_historial_routes(app, estado_service: EstadoService, historial: HistorialService):
    bp = Blueprint("historial", __name__, url_prefix="/historial")

    def _aplica():
        return (
            request.method in METODOS_QUE_MODIFICAN
            and not request.path.startswith(PREFIJOS_EXCLUIDOS)
        )

    @app.before_request
    def capturar_estado_previo():
        if _aplica():
            g.estado_previo = estado_service.capturar()

    @app.after_request
    def registrar_accion(response):
        estado_previo = g.pop("estado_previo", None)
        if estado_previo is None:
            return response
        estado_actual = estado_service.capturar()
        if EstadoService.huella(estado_actual) == EstadoService.huella(estado_previo):
            return response          # nothing changed -> not an action

        cuerpo = request.get_json(silent=True) or {}
        respuesta = response.get_json(silent=True) if response.is_json else None
        descripcion = describir_accion(
            request.endpoint or "", request.view_args or {}, cuerpo,
            respuesta if isinstance(respuesta, dict) else {},
        )
        historial.registrar(descripcion, estado_previo)
        return response

    @bp.route("", methods=["GET"])
    def listar():
        acciones = historial.listar()
        return jsonify({"cantidad": len(acciones), "acciones": acciones})

    @bp.route("/deshacer", methods=["POST"])
    def deshacer():
        accion = historial.deshacer()
        if accion is None:
            return jsonify({"error": "No hay acciones para deshacer."}), 409
        return jsonify({
            "mensaje": f"Se deshizo: {accion['descripcion']}",
            "accion": accion,
            "pendientes": len(historial.listar()),
        })

    @app.route("/sismos/acciones/deshacer", methods=["POST"])
    def deshacer_sismo_alias():
        accion = historial.deshacer()
        if accion is None:
            return jsonify({"error": "No hay acciones para deshacer."}), 409
        return jsonify({
            "mensaje": f"Se deshizo: {accion['descripcion']}",
            "accion": accion,
            "pendientes": len(historial.listar()),
        }), 200

    app.register_blueprint(bp)