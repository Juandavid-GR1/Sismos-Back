from datetime import datetime

from flask import Blueprint, jsonify, request

from src.business.services.AvlService import AvlService


def register_arbol_routes(app, avl_service: AvlService):
    arbol_bp = Blueprint("arbol", __name__, url_prefix="/arbol")

    def _nodo_a_dict(nodo, profundidad=0):
        if nodo is None:
            return None
        arbol = avl_service.get_arbol()
        fb = arbol.factorBalance(nodo)
        return {
            "clave": list(nodo.getClave()),
            "datos": nodo.getDatos(),
            "altura": nodo.getAltura(),
            "profundidad": profundidad,
            "factorBalance": fb,
            "balanceado": -1 <= fb <= 1,
            "hijoIzquierdo": _nodo_a_dict(nodo.getHijoIzquierdo(), profundidad + 1),
            "hijoDerecho": _nodo_a_dict(nodo.getHijoDerecho(), profundidad + 1),
        }

    @arbol_bp.route("/metricas", methods=["GET"])
    def metricas():
        limite = request.args.get("L", default=3, type=int)
        datos = avl_service.metricas(max(0, limite))
        # Backwards compatible fields used by the current frontend.
        datos["actualizadoEn"] = datetime.now().strftime("%H:%M:%S")
        return jsonify(datos)

    @arbol_bp.route("/topologia", methods=["GET"])
    def topologia():
        arbol = avl_service.get_arbol()
        return jsonify({
            "vacio": arbol.estaVacio(),
            "modoEstres": arbol.esModoEstres(),
            "raiz": _nodo_a_dict(arbol.getRaiz()),
        })

    @arbol_bp.route("/eventos/<int:sismo_id>", methods=["GET"])
    def evento_por_id(sismo_id):
        nodo = avl_service.buscar_por_id(sismo_id)
        if nodo is None:
            return jsonify({"error": "No existe un evento activo con ese id en el árbol"}), 404
        arbol = avl_service.get_arbol()
        profundidad = arbol.profundidadDe(nodo)
        return jsonify({
            "clave": list(nodo.getClave()),
            "datos": nodo.getDatos(),
            "altura": nodo.getAltura(),
            "profundidad": profundidad,
            "visitadosBusquedaPorClave": profundidad + 1,
            "factorBalance": arbol.factorBalance(nodo),
        })

    @arbol_bp.route("/auditoria", methods=["GET"])
    def auditoria():
        """Section 14 "Verificar estructura": one report per inconsistent
        node. In stress mode imbalance is reported as expected."""
        problemas = avl_service.auditar()
        errores = [p for p in problemas if p["tipo"] != "desbalance_esperado"]
        return jsonify({
            "valido": not errores,
            "modoEstres": avl_service.esta_en_modo_estres(),
            "problemas": problemas,
        })

    @arbol_bp.route("/modo-estres", methods=["POST"])
    def modo_estres():
        body = request.get_json(silent=True) or {}
        if body.get("activo", False):
            avl_service.activar_modo_estres()
        elif not avl_service.desactivar_modo_estres():
            return jsonify({
                "modoEstres": True,
                "error": "El árbol no cumple la condición AVL: ejecuta la recuperación global antes de volver al modo normal.",
            }), 409
        return jsonify({"modoEstres": avl_service.esta_en_modo_estres()})

    @arbol_bp.route("/recuperar-balance", methods=["POST"])
    def recuperar_balance():
        reporte = avl_service.recuperar_balance()
        return jsonify({
            "mensaje": "Recuperación completada",
            "rotacionesAplicadas": reporte["casosAplicados"],
            **reporte,
        })

    app.register_blueprint(arbol_bp)