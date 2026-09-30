class _NodoPila:

    __slots__ = ("dato", "siguiente")

    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None


class Pila:

    def __init__(self):
        self._cima = None
        self._tamano = 0

    def apilar(self, dato):
        nodo = _NodoPila(dato)
        nodo.siguiente = self._cima
        self._cima = nodo
        self._tamano += 1

    def estaVacia(self):
        return self._tamano == 0

    def desapilar(self):
        if self.estaVacia():
            raise Exception("Pila vacía")
        nodo = self._cima
        self._cima = nodo.siguiente
        self._tamano -= 1
        return nodo.dato

    def cima(self):
        if self.estaVacia():
            raise Exception("Pila vacía")
        return self._cima.dato

    def obtener_elementos(self):
        elementos = []
        actual = self._cima
        while actual is not None:
            elementos.append(actual.dato)
            actual = actual.siguiente
        return elementos

    def __len__(self):
        return self._tamano
