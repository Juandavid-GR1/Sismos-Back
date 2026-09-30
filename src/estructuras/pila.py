class _NodoPila:
  """Singly linked node used internally by Pila."""

  __slots__ = ("dato", "siguiente")

  def __init__(self, dato):
    self.dato = dato
    self.siguiente = None


class Pila:
  """
  LIFO stack implemented as a singly linked list (top = head).

  Costs:
    apilar, desapilar, cima, estaVacia, vaciar, len  
    obtener_elementos / elementos                      
  """

  def __init__(self):
    self._cima = None
    self._tamaño = 0

  def apilar(self, dato):
    """Pushes an element on top of the stack."""
    nodo = _NodoPila(dato)
    nodo.siguiente = self._cima
    self._cima = nodo
    self._tamaño += 1

  def estaVacia(self):
    return self._tamaño == 0

  def desapilar(self):
    """Pops and returns the top element."""
    if self.estaVacia():
      raise Exception("Pila vacía")
    nodo = self._cima
    self._cima = nodo.siguiente
    self._tamaño -= 1
    return nodo.dato

  def cima(self):
    """Returns the top element without removing it."""
    if self.estaVacia():
      raise Exception("Pila vacía")
    return self._cima.dato

  def obtener_elementos(self):
    """List copy of the elements, from the top (most recent) to the bottom."""
    elementos = []
    actual = self._cima
    while actual is not None:
      elementos.append(actual.dato)
      actual = actual.siguiente
    return elementos

  # Alias used by HistorialService (same result as obtener_elementos)
  def elementos(self):
    return self.obtener_elementos()

  def vaciar(self):
    """Removes every element: the old nodes are left without
    references and Python frees them."""
    self._cima = None
    self._tamaño = 0

  def __len__(self):
    return self._tamaño