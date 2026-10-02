from datetime import datetime

from flask import Blueprint, jsonify, request

from src.business.services.AvlService import AvlService


def register_arbol_routes(
    app,
    avl_service: AvlService,
    configuracion=None,
    sismo_repository=None,
    comparacion_service=None,
):
    arbol_bp = Blueprint("arbol", __name__, url_prefix="/arbol")

    def _nodo_a_dict(nodo, profundidad=0):
        if nodo is None:
            return None
        arbol = avl_service.get_arbol()
        fb = arbol.factorBalance(nodo)
        datos = nodo.getDatos() or {}
        return {
            "clave": list(nodo.getClave()),
            "datos": datos,
            "prioridad": nodo.getClave()[0],
            "accesoCostoso": bool(datos.get("acceso_costoso", False)),
            "limiteL": datos.get("limite_acceso"),
            "nodosVisitados": datos.get("nodos_visitados"),
            "altura": nodo.getAltura(),
            "profundidad": profundidad,
            "factorBalance": fb,
            "balanceado": -1 <= fb <= 1,
            "hijoIzquierdo": _nodo_a_dict(nodo.getHijoIzquierdo(), profundidad + 1),
            "hijoDerecho": _nodo_a_dict(nodo.getHijoDerecho(), profundidad + 1),
        }

    @arbol_bp.route("/metricas", methods=["GET"])
    def metricas():
        limite = request.args.get(
            "L",
            default=configuracion.limite_profundidad if configuracion else 3,
            type=int,
        )
        limite = max(0, limite)
        datos = avl_service.metricas(limite)
        # Backwards compatible fields used by the current frontend.
        datos["actualizadoEn"] = datetime.now().strftime("%H:%M:%S")
        return jsonify(datos)

    @arbol_bp.route("/configuracion", methods=["GET", "PUT", "PATCH"])
    def configuracion_arbol():
        if configuracion is None:
            return jsonify({"error": "Configuración no disponible."}), 500
        if request.method == "GET":
            return jsonify(configuracion.exportar()), 200
        body = request.get_json(silent=True) or {}
        try:
            resultado = configuracion.configurar(
                limite=body.get("limite_profundidad", body.get("L")),
                antiguedad=body.get(
                    "antiguedad_archivo_horas",
                    body.get("T"),
                ),
            )
        except (TypeError, ValueError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(resultado), 200

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
            "prioridad": nodo.getClave()[0],
            "accesoCostoso": bool((nodo.getDatos() or {}).get("acceso_costoso", False)),
            "limiteL": (nodo.getDatos() or {}).get("limite_acceso"),
            "altura": nodo.getAltura(),
            "profundidad": profundidad,
            "visitadosBusquedaPorClave": profundidad + 1,
            "factorBalance": arbol.factorBalance(nodo),
        })

    @arbol_bp.route("/comparacion", methods=["GET", "POST"])
    def comparacion_arboles():
        if comparacion_service is None or sismo_repository is None:
            return jsonify({"error": "Comparación de árboles no disponible."}), 500
        body = request.get_json(silent=True) or {}
        ids = body.get("ids") if request.method == "POST" else None
        ordenes = body.get("ordenes") if request.method == "POST" else None
        if ordenes is None:
            orden = request.args.get("orden")
            ordenes = [orden] if orden else None
        try:
            eventos = sismo_repository.get_all()
            if ids is not None:
                ids = {int(identificador) for identificador in ids}
                eventos = [evento for evento in eventos if evento.id in ids]
            claves = [evento.clave for evento in eventos if evento.clave is not None]
            if not claves:
                return jsonify({
                    "error": "No hay eventos activos con clave para comparar."
                }), 400
            return jsonify(comparacion_service.comparar(claves, ordenes)), 200
        except (TypeError, ValueError) as error:
            return jsonify({"error": str(error)}), 400

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