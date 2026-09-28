class _NodoCola:
  """Singly linked node used internally by Cola."""

  __slots__ = ("dato", "siguiente")

  def __init__(self, dato):
    self.dato = dato
    self.siguiente = None


class Cola:
  """
  FIFO queue implemented as a singly linked list with head and tail
  pointers.

  Costs:
    encolar     O(1)
    desencolar  O(1)   (a Python list with pop(0) would be O(n))
    frente      O(1)
    obtener_elementos  O(n)  (copy in reception order)
  Memory: O(n) nodes.
  """

  def __init__(self):
    self._cabeza = None
    self._cola = None
    self._tamano = 0

  def encolar(self, dato):
    """Adds an element at the end of the queue."""
    nodo = _NodoCola(dato)
    if self._cola is None:
      self._cabeza = nodo
    else:
      self._cola.siguiente = nodo
    self._cola = nodo
    self._tamano += 1

  def estaVacia(self):
    return self._tamano == 0

  def desencolar(self):
    """Removes and returns the first element (the oldest one)."""
    if self.estaVacia():
      raise Exception("Cola vacía")
    nodo = self._cabeza
    self._cabeza = nodo.siguiente
    if self._cabeza is None:
      self._cola = None
    self._tamano -= 1
    return nodo.dato

  def frente(self):
    """Returns the first element without removing it."""
    if self.estaVacia():
      raise Exception("Cola vacía")
    return self._cabeza.dato

  def obtener_elementos(self):
    """Returns a list copy of the elements in reception order."""
    elementos = []
    actual = self._cabeza
    while actual is not None:
      elementos.append(actual.dato)
      actual = actual.siguiente
    return elementos

  def __len__(self):
    return self._tamano