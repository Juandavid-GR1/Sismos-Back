from src.estructuras.arbol_bst import ArbolBST


class ArbolAVL(ArbolBST):
  """
  AVL tree ordered by K = (P, M, I).

  Additions over ArbolBST:
    * Stored heights (empty = -1, leaf = 0) and balance factor
      (left height - right height).
    * Normal mode: every insertion/deletion ends with a valid AVL.
    * Stress mode (section 8): the BST order is preserved but rotations
      are postponed; only heights along the modified path are updated.
    * Global recovery that fixes imbalances of any size (> 2 included).
    * Auxiliary index id -> node, so an event can be found by its id in
      O(1) even though the id is only the third component of the key.
    * Counters of LL/RR/LR/RL cases and elementary left/right rotations
      (section 14). A double case counts as one case and two rotations.
  """

  CASOS = ("LL", "RR", "LR", "RL")

  def __init__(self, comparador):
    super().__init__(comparador)
    self._modoEstres = False
    self._indice = {}
    self.reiniciarContadores()

  # ------------------------------------------------------------------
  # Counters
  # ------------------------------------------------------------------

  def reiniciarContadores(self):
    self._casos = {caso: 0 for caso in self.CASOS}
    self._giros = {"izquierda": 0, "derecha": 0}

  def getContadores(self):
    return {"casos": dict(self._casos), "giros": dict(self._giros)}

  def setContadores(self, contadores):
    """Restores counters (used by undo / versions / topology load)."""
    self._casos = {c: int(contadores.get("casos", {}).get(c, 0)) for c in self.CASOS}
    giros = contadores.get("giros", {})
    self._giros = {"izquierda": int(giros.get("izquierda", 0)),
                   "derecha": int(giros.get("derecha", 0))}

  # ------------------------------------------------------------------
  # Stress mode
  # ------------------------------------------------------------------

  def activarModoEstres(self):
    self._modoEstres = True

  def desactivarModoEstres(self):
    """Returns to normal mode only if the tree is already balanced;
    otherwise the caller must run recuperarBalanceGlobal() first."""
    if not self.estaBalanceado():
      return False
    self._modoEstres = False
    return True

  def esModoEstres(self):
    return self._modoEstres

  # ------------------------------------------------------------------
  # Heights and balance factor
  # ------------------------------------------------------------------

  def _altura(self, nodo):
    return -1 if nodo is None else nodo.getAltura()

  def _actualizarAltura(self, nodo):
    nodo.setAltura(max(self._altura(nodo.getHijoIzquierdo()),
                       self._altura(nodo.getHijoDerecho())) + 1)

  def _calcularFactorDeBalanceo(self, nodo):
    if nodo is None:
      return 0
    return self._altura(nodo.getHijoIzquierdo()) - self._altura(nodo.getHijoDerecho())

  factorBalance = _calcularFactorDeBalanceo

  def _actualizarAlturasHastaRaiz(self, nodo):
    """O(h): used in stress mode instead of recomputing the whole tree."""
    while nodo is not None:
      self._actualizarAltura(nodo)
      nodo = nodo.getPadre()

  def _recalcularAlturasCompleto(self):
    nodos = []
    self._posorden(self._raiz, nodos)
    for nodo in nodos:
      self._actualizarAltura(nodo)

  def estaBalanceado(self):
    return all(-1 <= self._calcularFactorDeBalanceo(n) <= 1 for n in self.inorden())

  # ------------------------------------------------------------------
  # Rotations
  # ------------------------------------------------------------------

  def _giroSimpleIzquierda(self, superior):
    mitad = superior.getHijoDerecho()
    hijoIzqMitad = mitad.getHijoIzquierdo()
    padreSuperior = superior.getPadre()

    mitad.setHijoIzquierdo(superior)
    superior.setPadre(mitad)
    superior.setHijoDerecho(hijoIzqMitad)
    if hijoIzqMitad is not None:
      hijoIzqMitad.setPadre(superior)
    self._enlazarConPadre(padreSuperior, superior, mitad)

    self._actualizarAltura(superior)
    self._actualizarAltura(mitad)
    self._giros["izquierda"] += 1
    return mitad

  def _giroSimpleDerecha(self, superior):
    mitad = superior.getHijoIzquierdo()
    hijoDerMitad = mitad.getHijoDerecho()
    padreSuperior = superior.getPadre()

    mitad.setHijoDerecho(superior)
    superior.setPadre(mitad)
    superior.setHijoIzquierdo(hijoDerMitad)
    if hijoDerMitad is not None:
      hijoDerMitad.setPadre(superior)
    self._enlazarConPadre(padreSuperior, superior, mitad)

    self._actualizarAltura(superior)
    self._actualizarAltura(mitad)
    self._giros["derecha"] += 1
    return mitad

  def _enlazarConPadre(self, padre, anterior, nuevo):
    nuevo.setPadre(padre)
    if padre is None:
      self._raiz = nuevo
    elif padre.getHijoIzquierdo() is anterior:
      padre.setHijoIzquierdo(nuevo)
    else:
      padre.setHijoDerecho(nuevo)

  def _detectarCasoDesbalanceo(self, superior, fb):
    if fb > 0:
      return "LL" if self._calcularFactorDeBalanceo(superior.getHijoIzquierdo()) >= 0 else "LR"
    return "RR" if self._calcularFactorDeBalanceo(superior.getHijoDerecho()) <= 0 else "RL"

  def _balancear(self, superior, caso):
    self._casos[caso] += 1
    if caso == "LL":
      return self._giroSimpleDerecha(superior)
    if caso == "RR":
      return self._giroSimpleIzquierda(superior)
    if caso == "LR":
      self._giroSimpleIzquierda(superior.getHijoIzquierdo())
      return self._giroSimpleDerecha(superior)
    self._giroSimpleDerecha(superior.getHijoDerecho())
    return self._giroSimpleIzquierda(superior)

  def _balancearDesdeNodo(self, nodo):
    """Walks up to the root fixing heights and rotating when needed."""
    actual = nodo
    while actual is not None:
      self._actualizarAltura(actual)
      fb = self._calcularFactorDeBalanceo(actual)
      if fb > 1 or fb < -1:
        actual = self._balancear(actual, self._detectarCasoDesbalanceo(actual, fb))
      actual = actual.getPadre()

  def _trasModificar(self, nodo):
    """Common tail of insert/delete: rotate (normal) or only fix
    heights (stress)."""
    if nodo is None:
      return
    if self._modoEstres:
      self._actualizarAlturasHastaRaiz(nodo)
    else:
      self._balancearDesdeNodo(nodo)

  # ------------------------------------------------------------------
  # Insert / delete keeping the id index in sync
  # ------------------------------------------------------------------

  def insertar(self, dato, datos):
    nuevo = self._insertarNodo(dato, datos)
    if nuevo is None:
      return False
    self._indice[dato[2]] = nuevo
    self._trasModificar(nuevo)
    return True

  def eliminar(self, dato):
    nodo = self.buscar(dato)
    if nodo is None:
      return False
    self._indice.pop(dato[2], None)
    padre = self._eliminar(nodo)
    self._trasModificar(padre)
    return True

  def _alMoverDatos(self, origen, destino):
    # The predecessor's event now lives in `destino`.
    self._indice[origen.getClave()[2]] = destino

  # ------------------------------------------------------------------
  # Id index
  # ------------------------------------------------------------------

  def buscarPorId(self, identificador):
    return self._indice.get(identificador)

  def eliminarPorId(self, identificador):
    nodo = self._indice.get(identificador)
    if nodo is None:
      return False
    return self.eliminar(nodo.getClave())

  def cantidadEventosActivos(self):
    return len(self._indice)

  def profundidadPorId(self, identificador):
    nodo = self.buscarPorId(identificador)
    return None if nodo is None else self.profundidadDe(nodo)

  # ------------------------------------------------------------------
  # Update (correction): remove with old key, reinsert with new key
  # ------------------------------------------------------------------

  def actualizar(self, identificador, claveNueva, datosNuevos):
    """
    Returns:
      "alta"                         -> it did not exist, inserted
      "actualizado_en_lugar"         -> same key, only payload changed
      "actualizado_con_reinsercion"  -> key changed, node relocated
    """
    nodo = self.buscarPorId(identificador)
    if nodo is None:
      self.insertar(claveNueva, datosNuevos)
      return "alta"

    if nodo.getClave() == claveNueva:
      nodo.setDatos(datosNuevos)
      return "actualizado_en_lugar"

    self.eliminar(nodo.getClave())
    self.insertar(claveNueva, datosNuevos)
    return "actualizado_con_reinsercion"

  # ------------------------------------------------------------------
  # Global recovery (section 8)
  # ------------------------------------------------------------------

  def recuperarBalanceGlobal(self):
    """
    Repeatedly fixes the DEEPEST unbalanced node (post order puts
    children before parents) until a full pass finds none.

    Order: each rotation is a local restructuring that keeps the in-order
    sequence, so the BST order is preserved.
    Termination: the node fixed is always the deepest unbalanced one, so
    its children subtrees are already AVL. A rotation there never makes
    that subtree taller, and any new imbalance it creates lies strictly
    inside a smaller subtree. Since the tree is finite, the loop ends
    (tests/test_arbol_avl.py checks it on degenerate trees with height
    differences far greater than 2). The tree is never rebuilt from a
    sorted list.

    Returns the number of cases applied (a double case counts once).
    """
    antes = self.getContadores()
    aplicados = 0
    while True:
      self._recalcularAlturasCompleto()
      nodos = []
      self._posorden(self._raiz, nodos)
      desbalanceado = next(
        (n for n in nodos if abs(self._calcularFactorDeBalanceo(n)) > 1), None
      )
      if desbalanceado is None:
        break
      fb = self._calcularFactorDeBalanceo(desbalanceado)
      self._balancear(desbalanceado, self._detectarCasoDesbalanceo(desbalanceado, fb))
      aplicados += 1

    despues = self.getContadores()
    self.ultimaRecuperacion = {
      "casosAplicados": aplicados,
      "casos": {c: despues["casos"][c] - antes["casos"][c] for c in self.CASOS},
      "giros": {g: despues["giros"][g] - antes["giros"][g] for g in ("izquierda", "derecha")},
    }
    return aplicados

  # ------------------------------------------------------------------
  # Audit (section 14)
  # ------------------------------------------------------------------

  def auditar(self):
    """
    Full structural check. Returns a list of problems, one dict per
    inconsistent node. Checks: global order by K (in-order strictly
    increasing, not only immediate children), unique ids, parent links,
    stored heights vs recomputed ones, balance factors and index.
    """
    problemas = []
    nodos = self.inorden()

    for anterior, actual in zip(nodos, nodos[1:]):
      if self._clave(anterior.getClave(), actual.getClave()) >= 0:
        problemas.append({"clave": list(actual.getClave()), "tipo": "orden",
                          "detalle": f"{anterior.getClave()} no es menor que {actual.getClave()}"})

    ids = {}
    for nodo in nodos:
      identificador = nodo.getClave()[2]
      if identificador in ids:
        problemas.append({"clave": list(nodo.getClave()), "tipo": "unicidad",
                          "detalle": f"id {identificador} repetido"})
      ids[identificador] = nodo
      for hijo in (nodo.getHijoIzquierdo(), nodo.getHijoDerecho()):
        if hijo is not None and hijo.getPadre() is not nodo:
          problemas.append({"clave": list(hijo.getClave()), "tipo": "referencia",
                            "detalle": "enlace padre inconsistente"})

    if self._raiz is not None and self._raiz.getPadre() is not None:
      problemas.append({"clave": list(self._raiz.getClave()), "tipo": "referencia",
                        "detalle": "la raíz tiene padre"})

    alturas = {}
    posorden = []
    self._posorden(self._raiz, posorden)
    for nodo in posorden:
      izq = alturas.get(id(nodo.getHijoIzquierdo()), -1)
      der = alturas.get(id(nodo.getHijoDerecho()), -1)
      real = max(izq, der) + 1
      alturas[id(nodo)] = real
      if nodo.getAltura() != real:
        problemas.append({"clave": list(nodo.getClave()), "tipo": "metadatos",
                          "detalle": f"altura almacenada {nodo.getAltura()} != recalculada {real}"})
      fb = izq - der
      if abs(fb) > 1:
        problemas.append({"clave": list(nodo.getClave()),
                          "tipo": "desbalance_esperado" if self._modoEstres else "desbalance",
                          "detalle": f"factor de balance {fb}"})

    if set(ids) != set(self._indice) or any(self._indice[i] is not ids[i] for i in ids if i in self._indice):
      problemas.append({"clave": None, "tipo": "indice",
                        "detalle": "el índice id->nodo no coincide con el árbol"})
    return problemas

  # ------------------------------------------------------------------
  # Costly access (section 9)
  # ------------------------------------------------------------------

  def eventosAccesoCostoso(self, limite, prioridadAlta=3):
    """High priority events whose node depth is strictly greater than L."""
    resultado = []
    for nodo in self.anchura():
      if nodo.getClave()[0] != prioridadAlta:
        continue
      profundidad = self.profundidadDe(nodo)
      if profundidad > limite:
        resultado.append({"nodo": nodo, "profundidad": profundidad,
                          "visitados": profundidad + 1})
    return resultado