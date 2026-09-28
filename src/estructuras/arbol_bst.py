from src.estructuras.nodo import Nodo
from src.estructuras.cola import Cola


class ArbolBST:

  def __init__(self, comparador):
    self._raiz = None
    self._clave = comparador
    self._comparaciones = 0

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
  # Inserción
  # ------------------------------------------------------------------

  def insertar(self, dato, datos):

    return self._insertarNodo(dato, datos) is not None

  def _insertarNodo(self, dato, datos):

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
  # Búsqueda
  # ------------------------------------------------------------------

  def buscar(self, dato):
    nodo, _ = self.buscarConConteo(dato)
    return nodo

  def buscarConConteo(self, dato):
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
  # Recorridos
  # ------------------------------------------------------------------

  def anchura(self):
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
  # Inicio comparaciones
  # ------------------------------------------------------------------

  def cantidadNodos(self):
    return len(self.inorden())

  def altura(self):
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
  # Eliminación (básica)
  # ------------------------------------------------------------------

  def eliminar(self, dato):
    nodo = self.buscar(dato)
    if nodo is None:
      return False
    self._eliminar(nodo)
    return True

  def _reemplazarEnPadre(self, nodo, hijo):
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
    izquierdo = nodo.getHijoIzquierdo()
    derecho = nodo.getHijoDerecho()

    if izquierdo is None or derecho is None:
      hijo = izquierdo if izquierdo is not None else derecho
      padre = self._reemplazarEnPadre(nodo, hijo)
      nodo.setHijoIzquierdo(None)
      nodo.setHijoDerecho(None)
      return padre

    predecesor = self._getPredecesor(nodo)
    self._alMoverDatos(predecesor, nodo)
    nodo.setClave(predecesor.getClave())
    nodo.setDatos(predecesor.getDatos())
    return self._eliminar(predecesor)

  def _alMoverDatos(self, origen, destino):
    pass

  def _getPredecesor(self, nodo):
    actual = nodo.getHijoIzquierdo()
    while actual.getHijoDerecho() is not None:
      actual = actual.getHijoDerecho()
    return actual

  # ------------------------------------------------------------------
  # Dibujar
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