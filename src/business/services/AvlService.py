"""
AvlService

Conecta el catálogo real de sismos con el árbol AVL de estructuras.
NO valida datos de negocio (eso ya lo hizo SismoService antes de
llamar aquí) -- solo se encarga de: calcular la prioridad vigente,
construir la clave K=(P,M,I), y sincronizar el árbol.

Diseño (sección 5 del enunciado): "Cada nodo del AVL representa
exactamente un evento activo. Su clave obligatoria es la tupla
ordenada K=(P,M,I)".

Este servicio es el único punto donde el árbol AVL se toca desde el
resto del backend -- nadie más debería importar ArbolAVL directamente.
"""

from typing import Optional

from src.estructuras.arbol_avl import ArbolAVL
from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService


def _comparador_claves(a, b):
    """Comparador lexicográfico de tuplas K=(P,M,I) -- ver sección 5
    del enunciado. Python ya compara tuplas de forma lexicográfica de
    manera nativa; esto solo traduce el resultado a -1/0/1."""
    return (a > b) - (a < b)


class AvlService:

    def __init__(self):
        self._arbol = ArbolAVL(_comparador_claves)

    def calcular_prioridad(
        self, magnitude: float, depth: float, zona_poblada: bool
    ) -> int:
        """Expone el cálculo de prioridad tal cual, por si algún
        controlador necesita mostrarla sin tocar el árbol (ej. antes
        de confirmar una creación)."""
        return PriorityKeyService.calcular_prioridad(magnitude, depth, zona_poblada)

    def registrar_evento(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        zona_poblada: bool,
        datos: dict,
    ) -> dict:
        """
        Alta o actualización de un evento en el AVL, CALCULANDO la
        prioridad aquí mismo. Úsalo cuando quien te llama todavía no
        tiene P/clave calculados.
        """
        prioridad = self.calcular_prioridad(magnitude, depth, zona_poblada)
        clave = PriorityKeyService.generar_clave(prioridad, magnitude, sismo_id)

        resultado = self._arbol.actualizar(sismo_id, clave, datos)

        return {"prioridad": prioridad, "clave": clave, "resultado": resultado}

    def sincronizar_desde_sismo(self, sismo) -> Optional[dict]:
        """
        Para cuando la clave YA llega calculada y validada desde
        afuera (ej. SismoService, que recibe prioridad/clave ya
        depurados desde reporte_service). NO recalcula nada -- solo
        confía en sismo.clave tal cual y sincroniza el árbol.

        Si sismo.clave todavía es None (evento recién creado, aún sin
        procesar por ningún reporte), no hace nada y retorna None --
        el árbol solo representa eventos con clave asignada.
        """
        if sismo.clave is None:
            return None

        resultado = self._arbol.actualizar(
            sismo.id,
            sismo.clave,
            {"status": sismo.status.value, "revision": sismo.revision},
        )

        return {"clave": sismo.clave, "resultado": resultado}

    @staticmethod
    def _payload(sismo) -> dict:
        return {"status": sismo.status.value, "revision": sismo.revision}

    def aplicar_correccion(self, anterior, nuevo) -> dict:
        """
        Moves an event from its old key to its new key as ONE operation
        and reports what happened to the tree (section 6, correction):

        * Same key  -> the node stays where it is, only its payload
          (revision, status) changes; the order is proven with the node's
          in-order neighbors.
        * Other key -> removed with the OLD key and reinserted with the NEW
          one (rotations happen as the current mode dictates).

        The rotations of this single action are measured as the counter
        difference before/after.
        """
        arbol = self._arbol
        antes = arbol.getContadores()
        profundidad_antes = arbol.profundidadPorId(anterior.id)

        resultado = arbol.actualizar(nuevo.id, nuevo.clave, self._payload(nuevo))

        nodo = arbol.buscarPorId(nuevo.id)
        despues = arbol.getContadores()
        return {
            "accion_arbol": (
                "sin_reinsercion"
                if resultado == "actualizado_en_lugar"
                else "reinsercion"
            ),
            "resultado": resultado,
            "profundidad_antes": profundidad_antes,
            "profundidad_despues": arbol.profundidadDe(nodo),
            "verificacion_orden": arbol.verificarOrdenLocal(nodo),
            "rotaciones": {
                "casos": {
                    c: despues["casos"][c] - antes["casos"][c] for c in arbol.CASOS
                },
                "giros": {
                    g: despues["giros"][g] - antes["giros"][g]
                    for g in ("izquierda", "derecha")
                },
            },
            "modo_estres": arbol.esModoEstres(),
        }

    def restaurar_evento(self, anterior, contadores: dict) -> None:
        """Rollback helper: puts the event back with its previous key and
        restores the rotation counters, so a failed action leaves no
        trace (no partial state)."""
        self._arbol.actualizar(anterior.id, anterior.clave, self._payload(anterior))
        self._arbol.setContadores(contadores)

    def contadores(self) -> dict:
        return self._arbol.getContadores()

    def cargar_desde(self, sismos) -> int:
        """Rebuilds the in-memory AVL from the persisted events at startup.
        Without this, after restarting Flask the catalog had events in
        sismos.json but the tree was EMPTY (the AVL lived only in memory).
        Returns how many events were inserted."""
        insertados = 0
        for sismo in sismos:
            if self.sincronizar_desde_sismo(sismo) is not None:
                insertados += 1
        # Loading is not part of the metrics of user operations.
        self._arbol.reiniciarContadores()
        return insertados

    def eliminar_evento(self, sismo_id: int) -> bool:
        """Retira un evento del catálogo activo (eliminación
        individual o archivo -- quien llama decide el motivo)."""
        return self._arbol.eliminarPorId(sismo_id)

    def profundidad_de(self, sismo_id: int):
        """Profundidad del nodo desde la raíz (raíz=0), o None si el
        id no está activo -- necesario para 'Consulta de un evento'
        (sección 6) y para 'acceso costoso' (sección 9)."""
        return self._arbol.profundidadPorId(sismo_id)

    def buscar_por_id(self, sismo_id: int):
        """Retorna el nodo (clave, altura, factor de balance) o None
        si el id no está activo en el árbol."""
        return self._arbol.buscarPorId(sismo_id)

    def cantidad_activos(self) -> int:
        return self._arbol.cantidadEventosActivos()

    def activar_modo_estres(self):
        self._arbol.activarModoEstres()

    def esta_en_modo_estres(self) -> bool:
        return self._arbol.esModoEstres()

    def desactivar_modo_estres(self) -> bool:
        """Returns False (and stays in stress mode) while the tree is not
        balanced: section 8 only allows returning to normal mode after the
        audit confirms the balance."""
        return self._arbol.desactivarModoEstres()

    def recuperar_balance(self) -> dict:
        """Runs the global recovery and returns the cases/rotations used."""
        self._arbol.recuperarBalanceGlobal()
        reporte = dict(self._arbol.ultimaRecuperacion)
        reporte["problemas"] = self._arbol.auditar()
        return reporte

    def auditar(self) -> list:
        return self._arbol.auditar()

    def metricas(self, limite_l: int = 3) -> dict:
        arbol = self._arbol
        base = arbol.metricas()
        costosos = arbol.eventosAccesoCostoso(limite_l)
        por_prioridad = {1: 0, 2: 0, 3: 0}
        pendientes = 0
        for nodo in arbol.inorden():
            por_prioridad[nodo.getClave()[0]] = (
                por_prioridad.get(nodo.getClave()[0], 0) + 1
            )
            datos = nodo.getDatos() or {}
            if str(datos.get("status", "")).lower().startswith("pend"):
                pendientes += 1
        base.update(
            {
                "balance": arbol.factorBalance(arbol.getRaiz()),
                "modoEstres": arbol.esModoEstres(),
                "balanceado": arbol.estaBalanceado(),
                "contadores": arbol.getContadores(),
                "porPrioridad": por_prioridad,
                "pendientes": pendientes,
                "limiteL": limite_l,
                "accesoCostoso": [
                    {
                        "clave": list(c["nodo"].getClave()),
                        "profundidad": c["profundidad"],
                        "visitados": c["visitados"],
                    }
                    for c in costosos
                ],
                "recorridos": {
                    "inorden": [list(n.getClave()) for n in arbol.inorden()],
                    "preorden": [list(n.getClave()) for n in arbol.preorden()],
                    "postorden": [list(n.getClave()) for n in arbol.posorden()],
                    "niveles": [list(n.getClave()) for n in arbol.anchura()],
                },
            }
        )
        return base

    def get_arbol(self) -> ArbolAVL:
        """Acceso directo al árbol, para el controlador que exponga
        /arbol/topologia y /arbol/metricas sobre el catálogo real (en
        vez de la API de prueba aislada del puerto 5050)."""
        return self._arbol
