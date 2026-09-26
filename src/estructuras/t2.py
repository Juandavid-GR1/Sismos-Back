from arbol_avl import ArbolAVL


def comparador_enteros(a, b):
    return (a > b) - (a < b)


def probar_caso(nombre_caso, secuencia):
    print("=" * 50)
    print("CASO:", nombre_caso, "-- secuencia de inserción:", secuencia)
    print("=" * 50)

    arbol = ArbolAVL(comparador_enteros)
    for valor in secuencia:
        arbol.insertar(valor, f"dato-{valor}")

    print()
    arbol.dibujar()

    raiz = arbol._raiz
    fb_raiz = arbol._calcularFactorDeBalanceo(raiz)
    print()
    print("Raíz final:", raiz.getClave(), "| altura:", raiz.getAltura(), "| factor de balance:", fb_raiz)

    if -1 <= fb_raiz <= 1:
        print("El árbol quedó balanceado")
    else:
        print("El árbol NO quedó balanceado")

    print()


# LL: cada valor nuevo es menor que el anterior -> se acumulan a la izquierda
probar_caso("LL", [30, 20, 10])

# RR: cada valor nuevo es mayor que el anterior -> se acumulan a la derecha
probar_caso("RR", [10, 20, 30])

# LR: el hijo izquierdo tiene un desbalance hacia la derecha
probar_caso("LR", [30, 10, 20])

# RL: el hijo derecho tiene un desbalance hacia la izquierda
probar_caso("RL", [10, 30, 20])