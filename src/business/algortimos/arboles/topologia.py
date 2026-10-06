"""
Nested (JSON) representation of a BST/AVL used by the interface to draw
a tree: {clave, datos, altura, profundidad, factorBalance, balanceado,
hijoIzquierdo, hijoDerecho}. Same shape as /arbol/topologia.

Built iteratively (post order) so a degenerate BST (ascending insertion)
never hits Python's recursion limit.
"""


def _altura(nodo):
    return -1 if nodo is None else nodo.getAltura()


def topologia_anidada(arbol) -> dict | None:
    raiz = arbol.getRaiz()
    if raiz is None:
        return None

    # Real heights are recomputed here: the plain BST does not keep them.
    alturas = {None: -1}
    convertidos = {}
    profundidades = {id(raiz): 0}
    orden = []
    pila = [raiz]
    while pila:
        nodo = pila.pop()
        orden.append(nodo)
        for hijo in (nodo.getHijoIzquierdo(), nodo.getHijoDerecho()):
            if hijo is not None:
                profundidades[id(hijo)] = profundidades[id(nodo)] + 1
                pila.append(hijo)

    for nodo in reversed(orden):      # children before parents
        izq, der = nodo.getHijoIzquierdo(), nodo.getHijoDerecho()
        h_izq = alturas[id(izq)] if izq is not None else -1
        h_der = alturas[id(der)] if der is not None else -1
        alturas[id(nodo)] = max(h_izq, h_der) + 1
        fb = h_izq - h_der
        datos = nodo.getDatos()
        convertidos[id(nodo)] = {
            "clave": list(nodo.getClave()),
            "datos": dict(datos) if isinstance(datos, dict) else datos,
            "altura": alturas[id(nodo)],
            "profundidad": profundidades[id(nodo)],
            "factorBalance": fb,
            "balanceado": -1 <= fb <= 1,
            "hijoIzquierdo": convertidos.get(id(izq)) if izq is not None else None,
            "hijoDerecho": convertidos.get(id(der)) if der is not None else None,
        }
    return convertidos[id(raiz)]
