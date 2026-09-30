from flask import Blueprint, jsonify, request

from src.business.services.ZonaService import ZonaService



class ZonaController:
    """
    Controller HTTP para las zonas geográficas.
    """

    def __init__(
        self,
        zona_service: ZonaService
    ):
        self.zona_service = zona_service

    def obtener_zonas(self):
        try:
            zonas = self.zona_service.get_all()

            return jsonify(zonas), 200

        except FileNotFoundError as error:
            return jsonify({
                "error": str(error)
            }), 500

        except Exception:
            return jsonify({
                "error": "Error interno al cargar las zonas."
            }), 500

    def comprobar_zona(self):
        try:
            data = request.get_json()

            longitud = data.get("longitud")
            latitud = data.get("latitud")

            if longitud is None or latitud is None:
                return jsonify({
                    "error": "Debe proporcionar longitud y latitud."
                }), 400

            zona_poblada = self.zona_service.punto_en_zona(
                longitud=float(longitud),
                latitud=float(latitud)
            )

            return jsonify({
                "longitud": float(longitud),
                "latitud": float(latitud),
                "zona_poblada": zona_poblada
            }), 200

        except ValueError:
            return jsonify({
                "error": "Las coordenadas deben ser numéricas."
            }), 400

        except Exception as error:
            return jsonify({
                "error": str(error)
            }), 500


def register_zona_routes(
    app,
    zona_service: ZonaService
):

    # Created per registration so it can be attached to a fresh app.
    zona_controller = Blueprint(
        "zona_controller",
        __name__,
        url_prefix="/zonas"
    )

    controller = ZonaController(
        zona_service
    )

    # GET /zonas
    zona_controller.add_url_rule(
        "",
        view_func=controller.obtener_zonas,
        methods=["GET"]
    )

    # POST /zonas/comprobar
    zona_controller.add_url_rule(
        "/comprobar",
        view_func=controller.comprobar_zona,
        methods=["POST"]
    )

    app.register_blueprint(
        zona_controller
    )