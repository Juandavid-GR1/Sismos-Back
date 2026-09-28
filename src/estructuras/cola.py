class _NodoCola:

  __slots__ = ("dato", "siguiente")

  def __init__(self, dato):
    self.dato = dato
    self.siguiente = None


class Cola:

  def __init__(self):
    self._cabeza = None
    self._cola = None
    self._tamano = 0

  def encolar(self, dato):

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
    if self.estaVacia():
      raise Exception("Cola vacía")
    nodo = self._cabeza
    self._cabeza = nodo.siguiente
    if self._cabeza is None:
      self._cola = None
    self._tamano -= 1
    return nodo.dato

  def frente(self):
    if self.estaVacia():
      raise Exception("Cola vacía")
    return self._cabeza.dato

  def obtener_elementos(self):
    elementos = []
    actual = self._cabeza
    while actual is not None:
      elementos.append(actual.dato)
      actual = actual.siguiente
    return elementos

  def __len__(self):
    return self._tamano