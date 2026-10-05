from flask import Blueprint, jsonify, request


def register_versiones_routes(app, versiones_service):
    blueprint = Blueprint("versiones", __name__, url_prefix="/versiones")

    @blueprint.route("", methods=["GET"])
    def listar_versiones():
        return jsonify({
            "cantidad": len(versiones_service.listar()),
            "versiones": versiones_service.listar(),
        }), 200

    @blueprint.route("", methods=["POST"])
    def guardar_version():
        data = request.get_json(silent=True) or {}
        try:
            resultado = versiones_service.guardar(data.get("nombre"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(resultado), 201

    @blueprint.route("/<string:nombre>", methods=["GET"])
    def obtener_version(nombre):
        try:
            return jsonify(versiones_service.obtener(nombre)), 200
        except (KeyError, ValueError) as error:
            return jsonify({"error": str(error)}), 404

    @blueprint.route("/<string:nombre>/restaurar", methods=["POST"])
    def restaurar_version(nombre):
        try:
            return jsonify(versiones_service.restaurar(nombre)), 200
        except KeyError as error:
            return jsonify({"error": str(error)}), 404
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @blueprint.route("/<string:nombre>", methods=["DELETE"])
    def eliminar_version(nombre):
        try:
            versiones_service.validar_nombre(nombre)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        if not versiones_service.repository.eliminar(nombre):
            return jsonify({"error": f"No existe la versión '{nombre}'."}), 404
        return jsonify({"mensaje": "Versión eliminada.", "nombre": nombre}), 200

    app.register_blueprint(blueprint)
