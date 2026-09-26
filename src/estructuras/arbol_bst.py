from nodo import Nodo
from cola import Cola

class ArbolBST:
  
  # constructor de clase
  def __init__(self, comparador):
    self._raiz = None
    self._clave = comparador

  # método para insertar un nuevo valor en el árbol
  def insertar(self, dato, datos):
    nodo = Nodo(dato, datos)
    if self._raiz is None:
      self._raiz = nodo
      print("El nodo ", dato, " se ha insertado como raiz.")
    else:
      self._insertar(nodo, self._raiz)

  # método privado recursivo para insertar
  def _insertar(self, nodo, raizActual):
    comparacion = self._clave(nodo.getClave(), raizActual.getClave())
    if comparacion == 0:
      print("El valor ya existe y no se puede insertar")
    else:
      if comparacion > 0:
        if raizActual.getHijoDerecho() is None:
          raizActual.setHijoDerecho(nodo)
          nodo.setPadre(raizActual)
          print("El nodo ", nodo.getClave() , " se ha insertado como hijo derecho de ", raizActual.getClave())
        else:
          self._insertar(nodo, raizActual.getHijoDerecho())
      else:
        if raizActual.getHijoIzquierdo() is None:
          raizActual.setHijoIzquierdo(nodo)
          nodo.setPadre(raizActual)
          print("El nodo ", nodo.getClave() , " se ha insertado como hijo izquierdo de ", raizActual.getClave())
        else:
          self._insertar(nodo, raizActual.getHijoIzquierdo())

  # método público para buscar un nodo con un valor específico
  def buscar(self, dato):
    if self.estaVacio():
      print("El árbol está vacío, no se encuentra el valor")
      return None
    else:
      return self._buscar(dato, self._raiz)

  # método para búsqueda recursiva de un valor en el BST
  def _buscar(self, dato, raizActual):
    comparacion = self._clave(dato, raizActual.getClave())
    if comparacion == 0:
      return raizActual
    else:
      if comparacion > 0:
        if raizActual.getHijoDerecho() is None:
          print("El nodo con valor " , dato, " no existe.")
          return None
        else:
          return self._buscar(dato, raizActual.getHijoDerecho())
      else:
        if raizActual.getHijoIzquierdo() is None:
          print("El nodo con valor " , dato, " no existe.")
          return None
        else:
          return self._buscar(dato, raizActual.getHijoIzquierdo())


  # método para verificar si el árbol está vacío o no
  def estaVacio(self):
    return self._raiz is None

  # método para mostrar el recorrido en anchura
  def anchura(self):
    if self.estaVacio():
      print("Árbol vacío")
      return []
    else:
      return self._anchura(self._raiz)

  # método privado de recorrido en anchura
  # ahora usa la clase Cola en vez de una lista con pop(0) improvisada
  def _anchura(self, raizActual):
    cola = Cola()
    recorrido = []
    cola.encolar(raizActual)
    while not cola.estaVacia():
      nodo = cola.desencolar()
      recorrido.append(nodo)
      if nodo.getHijoIzquierdo() is not None:
        cola.encolar(nodo.getHijoIzquierdo())
      if nodo.getHijoDerecho() is not None:
        cola.encolar(nodo.getHijoDerecho())

    return recorrido

  # método para mostrar el recorrido en profundidad (preorden)
  def preorden(self):
    if self.estaVacio():
      print("Árbol vacío")
      return []
    else:
      recorrido = []
      self._preorden(self._raiz, recorrido)
      return recorrido

  # método privado de recorrido en profundidad preorden
  def _preorden(self, raizActual, recorrido):
    if raizActual is not None:
      recorrido.append(raizActual)
      self._preorden(raizActual.getHijoIzquierdo(), recorrido)
      self._preorden(raizActual.getHijoDerecho(), recorrido)

  # método para mostrar el recorrido en profundidad (inorden)
  def inorden(self):
    if self.estaVacio():
      print("Árbol vacío")
      return []
    else:
      recorrido = []
      self._inorden(self._raiz, recorrido)
      return recorrido

  # método privado de recorrido en profundidad inorden
  def _inorden(self, raizActual, recorrido):
    if raizActual is not None:
      self._inorden(raizActual.getHijoIzquierdo(), recorrido)
      recorrido.append(raizActual)
      self._inorden(raizActual.getHijoDerecho(), recorrido)

  # método para mostrar el recorrido en profundidad (posorden)
  def posorden(self):
    if self.estaVacio():
      print("Árbol vacío")
      return []
    else:
      recorrido = []
      self._posorden(self._raiz, recorrido)
      return recorrido

  # método privado de recorrido en profundidad posorden
  def _posorden(self, raizActual, recorrido):
    if raizActual is not None:
      self._posorden(raizActual.getHijoIzquierdo(), recorrido)
      self._posorden(raizActual.getHijoDerecho(), recorrido)
      recorrido.append(raizActual)


# --------------------------------------------------
  # ELIMINAR
  # --------------------------------------------------

  # método público de eliminar
  def eliminar(self, dato):

    if self._raiz is None:

      print("El árbol está vacío")

    else:

      nodo = self.buscar(dato)

      if nodo is None:

        print(
          "No existe un nodo con valor ",
          dato
        )

      else:

        self._eliminar(
          nodo
        )

        print(
          "Se eliminó el nodo ",
          dato
        )


  # método privado de eliminar
  def _eliminar(self, nodo):

    # ------------------------------------------------
    # CASO 1
    # el nodo es una hoja
    # ------------------------------------------------

    if (
      nodo.getHijoIzquierdo() is None
      and
      nodo.getHijoDerecho() is None
    ):

      padre = nodo.getPadre()

      # si el nodo es la raíz
      if padre is None:

        self._raiz = None

      else:

        # se determina si es hijo izquierdo
        if padre.getHijoIzquierdo() == nodo:

          padre.setHijoIzquierdo(None)

        # de lo contrario es hijo derecho
        else:

          padre.setHijoDerecho(None)

      nodo.setPadre(None)

      return


    # ------------------------------------------------
    # CASO 2
    # solamente tiene hijo derecho
    # ------------------------------------------------

    if nodo.getHijoIzquierdo() is None:

      hijo = nodo.getHijoDerecho()
      padre = nodo.getPadre()

      # si el nodo es la raíz
      if padre is None:

        self._raiz = hijo

        hijo.setPadre(None)

      else:

        # si el nodo es hijo izquierdo
        if padre.getHijoIzquierdo() == nodo:

          padre.setHijoIzquierdo(hijo)

        else:

          padre.setHijoDerecho(hijo)

        # el hijo ahora apunta al padre del nodo eliminado
        hijo.setPadre(padre)

      nodo.setPadre(None)
      nodo.setHijoDerecho(None)

      return


    # ------------------------------------------------
    # CASO 2
    # solamente tiene hijo izquierdo
    # ------------------------------------------------

    if nodo.getHijoDerecho() is None:

      hijo = nodo.getHijoIzquierdo()
      padre = nodo.getPadre()

      # si el nodo es la raíz
      if padre is None:

        self._raiz = hijo

        hijo.setPadre(None)

      else:

        # si el nodo es hijo izquierdo
        if padre.getHijoIzquierdo() == nodo:

          padre.setHijoIzquierdo(hijo)

        else:

          padre.setHijoDerecho(hijo)

        # el hijo ahora apunta al padre del nodo eliminado
        hijo.setPadre(padre)

      nodo.setPadre(None)
      nodo.setHijoIzquierdo(None)

      return


    # ------------------------------------------------
    # CASO 3
    # el nodo tiene dos hijos
    #
    # se utiliza el PREDECESOR
    # ------------------------------------------------

    predecesor = self._getPredecesor(
      nodo
    )

    # se copian la clave y los datos del predecesor
    # en el nodo que se desea eliminar
    nodo.setClave(
      predecesor.getClave()
    )
    nodo.setDatos(
      predecesor.getDatos()
    )

    # se elimina físicamente el predecesor
    self._eliminar(
      predecesor
    )


  # --------------------------------------------------
  # OBTENER PREDECESOR
  #
  # retorna el mayor nodo del subárbol izquierdo
  # --------------------------------------------------

  def _getPredecesor(self, nodo):

    actual = nodo.getHijoIzquierdo()

    while actual.getHijoDerecho() is not None:

      actual = actual.getHijoDerecho()

    return actual


  # --------------------------------------------------
  # DIBUJAR
  # --------------------------------------------------

  def dibujar(self):

    if self._raiz is None:

      print("El árbol está vacío")

    else:

      print("\nÁrbol BST:")
      print("-----------")

      self._dibujar(
        self._raiz,
        "",
        "R"
      )


  # método para dibujar conceptualmente el árbol binario
  def _dibujar(self, raizActual, espacio, posicion):

    if raizActual is not None:

      self._dibujar(
        raizActual.getHijoDerecho(),
        espacio + "     ",
        "D"
      )

      print(
        espacio +
        posicion + "── " +
        str(raizActual.getClave())
      )

      self._dibujar(
        raizActual.getHijoIzquierdo(),
        espacio + "     ",
        "I"
      )