"""
RelojController

Expone el reloj de simulación del escenario (sección 3 del enunciado).
Mismo patrón de registro que los demás controladores con dependencias
inyectadas (register_X_routes(app, servicio)).
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from src.business.services.RelojService import RelojFueraDeOrdenError, RelojService


def _iso_utc(fecha: datetime) -> str:
    """The clock is kept in UTC: answer with an explicit offset so the
    browser does not read it as local time."""
    return fecha.replace(tzinfo=timezone.utc).isoformat()


def register_reloj_routes(app, reloj_service: RelojService):
    reloj_bp = Blueprint("reloj", __name__, url_prefix="/reloj")

    @reloj_bp.errorhandler(RelojFueraDeOrdenError)
    def handle_reloj_error(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400

    @reloj_bp.route("", methods=["GET"])
    def obtener_reloj():
        return jsonify({
            "reloj_actual": _iso_utc(reloj_service.obtener_reloj())
        })

    @reloj_bp.route("/avanzar", methods=["POST"])
    def avanzar_reloj():
        """
        Body esperado (uno de los dos, no ambos):
        { "fecha_hora": "2026-09-25T10:00:00" }   -> avance absoluto
        { "horas": 6 }                             -> avance relativo
        """
        data = request.get_json(silent=True) or {}

        if "fecha_hora" in data:
            try:
                nueva_fecha = datetime.fromisoformat(str(data["fecha_hora"]).replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Bad Request", "message": "fecha_hora debe estar en formato ISO 8601."}), 400
            reloj_service.avanzar_a(nueva_fecha)
        elif "horas" in data:
            try:
                horas = float(data["horas"])
            except (TypeError, ValueError):
                return jsonify({"error": "Bad Request", "message": "horas debe ser un número."}), 400
            reloj_service.avanzar_horas(horas)
        else:
            return jsonify({
                "error": "Bad Request",
                "message": "Se requiere el campo 'fecha_hora' (absoluto) u 'horas' (relativo)."
            }), 400

        return jsonify({
            "mensaje": "Reloj avanzado",
            "reloj_actual": _iso_utc(reloj_service.obtener_reloj())
        })

    app.register_blueprint(reloj_bp)