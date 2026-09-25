from nodo import Nodo
from arbol_bst import ArbolBST
from comparador_eventos import comparador_eventos

prueba1 = [
    ((3, 7.8, 10), {"id": 10, "nota": "M=7.8, prioridad alta por M>=6.0"}),
    ((3, 7.8, 16), {"id": 16, "nota": "caso limite: M=4.5, H=30.0, borde poblada"}),
    ((2, 4.5, 17), {"id": 17, "nota": "mismo M/H que 16, pero zona no poblada"}),
    ((1, 3.0, 18), {"id": 18, "nota": "empate P/M con 19, id menor"}),
    ((1, 3.0, 19), {"id": 19, "nota": "empate P/M con 18, id mayor"}),
    ((2, 4.6, 20), {"id": 20, "nota": "M>=4.5 pero fuera de cualquier zona"}),
]

arbol = ArbolBST(comparador_eventos)

for clave, datos in prueba1:
    arbol.insertar(clave, datos)


print("\nRecorrido inorden")
for nodo in arbol.inorden():
    print(nodo.getClave())

print(arbol.buscar((1,3,18)))

#arbol.eliminar((1, 3, 18))