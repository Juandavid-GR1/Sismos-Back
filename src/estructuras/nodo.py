class Nodo:

  """
  Class for ordered binary trees (BST / AVL).
  The key is separated from the data because the tree only needs
  compare the key that is a tuple to decide positions, this allows
  use the same Node for the BST and for the AVL without duplicating code.
  """

  # constructor de la clase 
  def __init__(self, clave, datos, altura=0):
    self._clave = clave
    self._datos = datos
    self._hijoIzquierdo = None
    self._hijoDerecho = None
    self._padre = None
    self._altura = altura

  # obtiene la clave del nodo
  def getClave(self):
    return self._clave

  # método para asignar la clave a un nodo
  def setClave(self, clave):
    self._clave = clave

  # obtiene los datos del nodo
  def getDatos(self):
    return self._datos

  # método para asignar datos a un nodo
  def setDatos(self, datos):
    self._datos = datos

  # método para obtener el hijo izquierdo del nodo
  def getHijoIzquierdo(self):
    return self._hijoIzquierdo

  # método de asignar un nodo como hijo izquierdo
  def setHijoIzquierdo(self, nodo):
    self._hijoIzquierdo = nodo

  # método para obtener el hijo derecho del nodo
  def getHijoDerecho(self):
    return self._hijoDerecho

  # método de asignar un nodo como hijo derecho
  def setHijoDerecho(self, nodo):
    self._hijoDerecho = nodo

  # método para obtener el padre del nodo
  def getPadre(self):
    return self._padre

  # método para asignar un nodo como padre
  def setPadre(self, nodo):
    self._padre = nodo

  # método para obtener la altura de un nodo
  def getAltura(self):
    return self._altura

  # método para asignar altura a un nodo
  def setAltura(self, altura):
    self._altura = altura