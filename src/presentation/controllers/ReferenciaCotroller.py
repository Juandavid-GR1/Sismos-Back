from flask import Blueprint, jsonify, request


def register_referencia_routes(app, referencia_service):
    blueprint = Blueprint(
        "referencia_sismo",
        __name__,
        url_prefix="/referencias-sismo",
    )

    @blueprint.route("/<int:sismo_id>", methods=["GET"])
    def obtener_referencias_sismo(sismo_id):
        try:
            consulta = referencia_service.consulta_asociaciones(sismo_id)
        except ValueError as error:
            return jsonify({"error": str(error)}), 404
        return jsonify({
            "sismo_id": sismo_id,
            "referencias": consulta["candidatos"],
            "candidatos": consulta["candidatos"],
            "referencia": consulta["referencia"],
            "estado": consulta["estado"],
            "eventos_que_lo usan_como_referencia": (
                consulta["eventos_que_lo usan_como_referencia"]
            ),
        }), 200

    @blueprint.route("/<int:sismo_id>/detalle", methods=["GET"])
    def obtener_detalle_asociaciones(sismo_id):
        try:
            return jsonify(referencia_service.consulta_asociaciones(sismo_id)), 200
        except ValueError as error:
            return jsonify({"error": str(error)}), 404

    @blueprint.route("/<int:sismo_id>/usos", methods=["GET"])
    def obtener_usos_referencia(sismo_id):
        if referencia_service._evento_por_id(sismo_id) is None:
            return jsonify({"error": "El sismo no existe"}), 404
        return jsonify({
            "referencia_id": sismo_id,
            "eventos": referencia_service.eventos_que_usan_como_referencia(sismo_id),
        }), 200

    @blueprint.route("/<int:sismo_id>/actual", methods=["GET"])
    def obtener_referencia_actual(sismo_id):
        if referencia_service._evento_por_id(sismo_id) is None:
            return jsonify({"error": "El sismo no existe"}), 404
        referencia = referencia_service.obtener_referencia(sismo_id)
        return jsonify({
            "sismo_id": sismo_id,
            "referencia": referencia.to_dict() if referencia else None,
        }), 200

    @blueprint.route("", methods=["POST"])
    def guardar_referencia():
        data = request.get_json(silent=True) or {}
        if data.get("sismo_id") is None or data.get("referencia_id") is None:
            return jsonify({
                "error": "Los campos sismo_id y referencia_id son obligatorios"
            }), 400
        try:
            relacion = referencia_service.guardar_referencia(
                int(data["sismo_id"]), int(data["referencia_id"])
            )
        except (TypeError, ValueError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({
            "mensaje": "Referencia de sismo guardada correctamente",
            "referencia": relacion.to_dict(),
        }), 201

    @blueprint.route("/configuracion", methods=["GET", "PUT", "PATCH"])
    def configuracion():
        if request.method == "GET":
            return jsonify(referencia_service.configuracion()), 200
        data = request.get_json(silent=True) or {}
        try:
            configuracion_actual = referencia_service.configurar(
                data.get("ventana_horas", data.get("W")),
                data.get("radio_km", data.get("R")),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(configuracion_actual), 200

    app.register_blueprint(blueprint)
