from arbol_bst import ArbolBST


class ArbolAVL(ArbolBST):

  def __init__(self, comparador):
    super().__init__(comparador)
    self._modoEstres = False

  # --------------------------------------------------
  # MODO ESTRÉS
  # --------------------------------------------------

  def activarModoEstres(self):
    self._modoEstres = True

  def desactivarModoEstres(self):
    self._modoEstres = False

  def esModoEstres(self):
    return self._modoEstres

  def _recalcularAlturasCompleto(self):
    """Recorre todo el árbol y calcula la altura de cada nodo de
    abajo hacia arriba."""
    nodos = []
    self._posorden(self._raiz, nodos)
    for nodo in nodos:
      self._actualizarAltura(nodo)

  def _altura(self, nodo):
    if nodo is None:
      return -1
    return nodo.getAltura()

  def _actualizarAltura(self, nodo):
    hIzq = self._altura(nodo.getHijoIzquierdo())
    hDer = self._altura(nodo.getHijoDerecho())
    nodo.setAltura(max(hIzq, hDer) + 1)

  def _calcularFactorDeBalanceo(self, nodo):
    hIzq = self._altura(nodo.getHijoIzquierdo())
    hDer = self._altura(nodo.getHijoDerecho())
    return hIzq - hDer

  def _giroSimpleIzquierda(self, superior):
    mitad = superior.getHijoDerecho()
    hijoIzqMitad = mitad.getHijoIzquierdo()
    padreSuperior = superior.getPadre()

    mitad.setHijoIzquierdo(superior)
    superior.setPadre(mitad)

    superior.setHijoDerecho(hijoIzqMitad)
    if hijoIzqMitad is not None:
      hijoIzqMitad.setPadre(superior)

    mitad.setPadre(padreSuperior)

    if padreSuperior is None:
      self._raiz = mitad
    else:
      if padreSuperior.getHijoIzquierdo() is superior:
        padreSuperior.setHijoIzquierdo(mitad)
      else:
        padreSuperior.setHijoDerecho(mitad)

    self._actualizarAltura(superior)
    self._actualizarAltura(mitad)

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

    mitad.setPadre(padreSuperior)

    if padreSuperior is None:
      self._raiz = mitad
    else:
      if padreSuperior.getHijoIzquierdo() is superior:
        padreSuperior.setHijoIzquierdo(mitad)
      else:
        padreSuperior.setHijoDerecho(mitad)

    self._actualizarAltura(superior)
    self._actualizarAltura(mitad)

    return mitad

  def _detectarCasoDesbalanceo(self, superior, fb):
    if fb > 0:
      fbHijo = self._calcularFactorDeBalanceo(superior.getHijoIzquierdo())
      if fbHijo > 0:
        caso = "LL"
      else:
        caso = "LR"
    else:
      fbHijo = self._calcularFactorDeBalanceo(superior.getHijoDerecho())
      if fbHijo > 0:
        caso = "RL"
      else:
        caso = "RR"
    return caso

  def _balancear(self, superior, caso):
    match caso:
      case "LL":
        return self._giroSimpleDerecha(superior)
      case "RR":
        return self._giroSimpleIzquierda(superior)
      case "LR":
        self._giroSimpleIzquierda(superior.getHijoIzquierdo())
        return self._giroSimpleDerecha(superior)
      case "RL":
        self._giroSimpleDerecha(superior.getHijoDerecho())
        return self._giroSimpleIzquierda(superior)

  def _balancearDesdeNodo(self, nodo):
    actual = nodo
    while actual is not None:
      self._actualizarAltura(actual)
      fb = self._calcularFactorDeBalanceo(actual)

      if fb > 1 or fb < -1:
        caso = self._detectarCasoDesbalanceo(actual, fb)
        print("  -> Desbalance detectado en", actual.getClave(), "| fb =", fb, "| caso:", caso)
        actual = self._balancear(actual, caso)

      actual = actual.getPadre()

  def insertar(self, dato, datos):
    super().insertar(dato, datos)

    if self._modoEstres:
      self._recalcularAlturasCompleto()
    else:
      nodoInsertado = self.buscar(dato)
      if nodoInsertado is not None:
        self._balancearDesdeNodo(nodoInsertado)

  # --------------------------------------------------
  # RECUPERACIÓN GLOBAL DE BALANCE 
  # --------------------------------------------------

  def recuperarBalanceGlobal(self):
    rotaciones_aplicadas = 0
    encontro_desbalance = True

    while encontro_desbalance:
      encontro_desbalance = False
      self._recalcularAlturasCompleto()

      nodos = []
      self._posorden(self._raiz, nodos)

      for nodo in nodos:
        fb = self._calcularFactorDeBalanceo(nodo)
        if fb > 1 or fb < -1:
          caso = self._detectarCasoDesbalanceo(nodo, fb)
          self._balancear(nodo, caso)
          rotaciones_aplicadas += 1
          encontro_desbalance = True
          break  # se reinicia la vuelta completa, porque la
                 # estructura del árbol acaba de cambiar

    return rotaciones_aplicadas

  def eliminar(self, dato):
    if self._raiz is None:
      print("El árbol está vacío")
    else:
      nodo = self.buscar(dato)
      if nodo is None:
        print("No existe un nodo con valor ", dato)
      else:
        self._eliminarAVL(nodo)
        print("Se eliminó el nodo ", dato)

  def _eliminarAVL(self, nodo):
    if nodo.getHijoIzquierdo() is None and nodo.getHijoDerecho() is None:
      padre = nodo.getPadre()
      if padre is None:
        self._raiz = None
      else:
        if padre.getHijoIzquierdo() is nodo:
          padre.setHijoIzquierdo(None)
        else:
          padre.setHijoDerecho(None)
        self._balancearDesdeNodo(padre)
      nodo.setPadre(None)
      return

    if nodo.getHijoIzquierdo() is None:
      hijo = nodo.getHijoDerecho()
      padre = nodo.getPadre()
      if padre is None:
        self._raiz = hijo
        hijo.setPadre(None)
      else:
        if padre.getHijoIzquierdo() is nodo:
          padre.setHijoIzquierdo(hijo)
        else:
          padre.setHijoDerecho(hijo)
        hijo.setPadre(padre)
        self._balancearDesdeNodo(padre)
      nodo.setPadre(None)
      nodo.setHijoDerecho(None)
      return

    if nodo.getHijoDerecho() is None:
      hijo = nodo.getHijoIzquierdo()
      padre = nodo.getPadre()
      if padre is None:
        self._raiz = hijo
        hijo.setPadre(None)
      else:
        if padre.getHijoIzquierdo() is nodo:
          padre.setHijoIzquierdo(hijo)
        else:
          padre.setHijoDerecho(hijo)
        hijo.setPadre(padre)
        self._balancearDesdeNodo(padre)
      nodo.setPadre(None)
      nodo.setHijoIzquierdo(None)
      return

    predecesor = self._getPredecesor(nodo)
    nodo.setClave(predecesor.getClave())
    nodo.setDatos(predecesor.getDatos())
    self._eliminarAVL(predecesor)