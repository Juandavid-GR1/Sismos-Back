from src.estructuras.nodo import Nodo
from src.estructuras.cola import Cola


class ArbolBST:
  """
  Unbalanced binary search tree ordered by a comparator function.

  The comparator receives two keys and returns a negative number, zero
  or a positive number (like C's strcmp). For seismic events the key is
  the tuple K = (P, M, I) and the comparison is lexicographic.

  This class is also the base of ArbolAVL: the AVL only adds heights,
  rotations and the id index on top of these operations. That way the
  BST used for the AVL-vs-BST comparison (sections 11 and 12) and the
  AVL share exactly the same comparator and insertion path.

  Search and insertion are iterative to avoid Python's recursion limit
  when the tree degenerates (e.g. ascending insertion in the BST).
  """

  def __init__(self, comparador):
    self._raiz = None
    self._clave = comparador
    # Accumulated number of key comparisons (for BST vs AVL metrics).
    self._comparaciones = 0

  # ------------------------------------------------------------------
  # Basic accessors
  # ------------------------------------------------------------------

  def getRaiz(self):
    return self._raiz

  def estaVacio(self):
    return self._raiz is None

  def getComparaciones(self):
    return self._comparaciones

  def reiniciarComparaciones(self):
    self._comparaciones = 0

  def _comparar(self, a, b):
    self._comparaciones += 1
    return self._clave(a, b)

  # ------------------------------------------------------------------
  # Insertion
  # ------------------------------------------------------------------

  def insertar(self, dato, datos):
    """Inserts key `dato` with payload `datos`.
    Returns True if inserted, False if the key already existed."""
    return self._insertarNodo(dato, datos) is not None

  def _insertarNodo(self, dato, datos):
    """Inserts and returns the new node, or None if the key exists.
    Smaller keys go to the left child and larger keys to the right."""
    nuevo = Nodo(dato, datos)
    if self._raiz is None:
      self._raiz = nuevo
      return nuevo

    actual = self._raiz
    while True:
      comparacion = self._comparar(dato, actual.getClave())
      if comparacion == 0:
        return None
      if comparacion > 0:
        if actual.getHijoDerecho() is None:
          actual.setHijoDerecho(nuevo)
          break
        actual = actual.getHijoDerecho()
      else:
        if actual.getHijoIzquierdo() is None:
          actual.setHijoIzquierdo(nuevo)
          break
        actual = actual.getHijoIzquierdo()

    nuevo.setPadre(actual)
    return nuevo

  # ------------------------------------------------------------------
  # Search
  # ------------------------------------------------------------------

  def buscar(self, dato):
    """Returns the node with key `dato` or None."""
    nodo, _ = self.buscarConConteo(dato)
    return nodo

  def buscarConConteo(self, dato):
    """Returns (node or None, visited nodes). For an existing key the
    number of visited nodes equals its depth + 1 (section 9)."""
    visitados = 0
    actual = self._raiz
    while actual is not None:
      visitados += 1
      comparacion = self._comparar(dato, actual.getClave())
      if comparacion == 0:
        return actual, visitados
      actual = actual.getHijoDerecho() if comparacion > 0 else actual.getHijoIzquierdo()
    return None, visitados

  # ------------------------------------------------------------------
  # Traversals (iterative where recursion could get deep)
  # ------------------------------------------------------------------

  def anchura(self):
    """Level order traversal using the project's own FIFO queue."""
    recorrido = []
    if self._raiz is None:
      return recorrido
    cola = Cola()
    cola.encolar(self._raiz)
    while not cola.estaVacia():
      nodo = cola.desencolar()
      recorrido.append(nodo)
      if nodo.getHijoIzquierdo() is not None:
        cola.encolar(nodo.getHijoIzquierdo())
      if nodo.getHijoDerecho() is not None:
        cola.encolar(nodo.getHijoDerecho())
    return recorrido

  def preorden(self):
    recorrido = []
    pila = [self._raiz] if self._raiz is not None else []
    while pila:
      nodo = pila.pop()
      recorrido.append(nodo)
      if nodo.getHijoDerecho() is not None:
        pila.append(nodo.getHijoDerecho())
      if nodo.getHijoIzquierdo() is not None:
        pila.append(nodo.getHijoIzquierdo())
    return recorrido

  def inorden(self):
    recorrido = []
    pila = []
    actual = self._raiz
    while pila or actual is not None:
      while actual is not None:
        pila.append(actual)
        actual = actual.getHijoIzquierdo()
      actual = pila.pop()
      recorrido.append(actual)
      actual = actual.getHijoDerecho()
    return recorrido

  def posorden(self):
    recorrido = []
    self._posorden(self._raiz, recorrido)
    return recorrido

  def _posorden(self, raizActual, recorrido):
    """Iterative post order (children before parent). Kept with the
    old signature because the AVL uses it."""
    if raizActual is None:
      return
    pila = [raizActual]
    salida = []
    while pila:
      nodo = pila.pop()
      salida.append(nodo)
      if nodo.getHijoIzquierdo() is not None:
        pila.append(nodo.getHijoIzquierdo())
      if nodo.getHijoDerecho() is not None:
        pila.append(nodo.getHijoDerecho())
    recorrido.extend(reversed(salida))

  # ------------------------------------------------------------------
  # Structural metrics (section 11/12: AVL vs BST comparison)
  # ------------------------------------------------------------------

  def cantidadNodos(self):
    return len(self.inorden())

  def altura(self):
    """Tree height computed from scratch (empty = -1, leaf = 0)."""
    if self._raiz is None:
      return -1
    maxima = -1
    pila = [(self._raiz, 0)]
    while pila:
      nodo, profundidad = pila.pop()
      maxima = max(maxima, profundidad)
      if nodo.getHijoIzquierdo() is not None:
        pila.append((nodo.getHijoIzquierdo(), profundidad + 1))
      if nodo.getHijoDerecho() is not None:
        pila.append((nodo.getHijoDerecho(), profundidad + 1))
    return maxima

  def contarHojas(self):
    return sum(
      1 for n in self.inorden()
      if n.getHijoIzquierdo() is None and n.getHijoDerecho() is None
    )

  def profundidadDe(self, nodo):
    """Depth of a node (root = 0), walking up through parent links."""
    profundidad = 0
    actual = nodo.getPadre()
    while actual is not None:
      profundidad += 1
      actual = actual.getPadre()
    return profundidad

  def metricas(self):
    raiz = self._raiz.getClave() if self._raiz is not None else None
    altura = self.altura()
    return {
      "raiz": list(raiz) if isinstance(raiz, tuple) else raiz,
      "cantidadNodos": self.cantidadNodos(),
      "altura": altura,
      "profundidadMaxima": altura,
      "hojas": self.contarHojas(),
      "comparaciones": self._comparaciones,
    }

  # ------------------------------------------------------------------
  # Deletion (plain BST, the AVL overrides it)
  # ------------------------------------------------------------------

  def eliminar(self, dato):
    """Removes the node with key `dato`. Returns True if it existed."""
    nodo = self.buscar(dato)
    if nodo is None:
      return False
    self._eliminar(nodo)
    return True

  def _reemplazarEnPadre(self, nodo, hijo):
    """Links `hijo` in the place `nodo` occupied under its parent."""
    padre = nodo.getPadre()
    if padre is None:
      self._raiz = hijo
    elif padre.getHijoIzquierdo() is nodo:
      padre.setHijoIzquierdo(hijo)
    else:
      padre.setHijoDerecho(hijo)
    if hijo is not None:
      hijo.setPadre(padre)
    nodo.setPadre(None)
    return padre

  def _eliminar(self, nodo):
    """Returns the parent of the node physically removed (the point
    where the AVL must start rebalancing)."""
    izquierdo = nodo.getHijoIzquierdo()
    derecho = nodo.getHijoDerecho()

    if izquierdo is None or derecho is None:
      hijo = izquierdo if izquierdo is not None else derecho
      padre = self._reemplazarEnPadre(nodo, hijo)
      nodo.setHijoIzquierdo(None)
      nodo.setHijoDerecho(None)
      return padre

    # Two children: copy the in-order predecessor into this node and
    # physically remove the predecessor (it has at most one child).
    predecesor = self._getPredecesor(nodo)
    self._alMoverDatos(predecesor, nodo)
    nodo.setClave(predecesor.getClave())
    nodo.setDatos(predecesor.getDatos())
    return self._eliminar(predecesor)

  def _alMoverDatos(self, origen, destino):
    """Hook: the AVL overrides it to keep its id index in sync."""
    pass

  def _getPredecesor(self, nodo):
    actual = nodo.getHijoIzquierdo()
    while actual.getHijoDerecho() is not None:
      actual = actual.getHijoDerecho()
    return actual

  # ------------------------------------------------------------------
  # Console drawing (debug only)
  # ------------------------------------------------------------------

  def dibujar(self):
    if self._raiz is None:
      print("El árbol está vacío")
    else:
      print("\nÁrbol:")
      print("-----------")
      self._dibujar(self._raiz, "", "R")

  def _dibujar(self, raizActual, espacio, posicion):
    if raizActual is not None:
      self._dibujar(raizActual.getHijoDerecho(), espacio + "     ", "D")
      print(espacio + posicion + "── " + str(raizActual.getClave()) +
            " (h=" + str(raizActual.getAltura()) + ")")
      self._dibujar(raizActual.getHijoIzquierdo(), espacio + "     ", "I")