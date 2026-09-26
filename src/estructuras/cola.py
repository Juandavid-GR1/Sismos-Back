class Cola:

  # constructor de clase
  def __init__(self):
    self._cola = []

  # Método para agregar un elemento a la cola
  def encolar(self, dato):
    self._cola.append(dato)

  # Método para validar si la cola está vacía
  def estaVacia(self):
    return len(self._cola) == 0

  # Método que permite desencolar un elemento (el primero que entró) de la cola
  def desencolar(self):
    if not self.estaVacia():
      return self._cola.pop(0)
    else:
      raise Exception("Cola vacía")

  # Método que permite obtener sin eliminar
  def frente(self):
    if not self.estaVacia():
      return self._cola[0]
    else:
      raise Exception("Cola vacía")