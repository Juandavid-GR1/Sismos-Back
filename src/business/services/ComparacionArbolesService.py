from __future__ import annotations

from typing import Iterable

from src.estructuras.arbol_avl import ArbolAVL
from src.estructuras.arbol_bst import ArbolBST
from src.estructuras.comparador_eventos import comparador_eventos
from src.business.algortimos.arboles.topologia import topologia_anidada


class ComparacionArbolesService:
    """Builds isolated AVL/BST trees to compare structural performance."""

    ORDENES_VALIDOS = {"original", "ascendente", "descendente"}

    def comparar(self, claves: Iterable[tuple], ordenes: list[str] | None = None) -> dict:
        claves = [tuple(clave) for clave in claves]
        ordenes = ordenes or ["original", "ascendente", "descendente"]
        invalidas = [orden for orden in ordenes if orden not in self.ORDENES_VALIDOS]
        if invalidas:
            raise ValueError(
                f"Ordenes no validos: {', '.join(invalidas)}. "
                f"Use: {', '.join(sorted(self.ORDENES_VALIDOS))}."
            )

        resultados = []
        for orden in ordenes:
            secuencia = self._ordenar(claves, orden)
            avl = ArbolAVL(comparador_eventos)
            bst = ArbolBST(comparador_eventos)
            for clave in secuencia:
                datos = {"id": clave[2]}
                if not avl.insertar(clave, datos) or not bst.insertar(clave, datos):
                    raise ValueError(f"La clave duplicada {clave} no permite comparar.")

            inserciones_avl = avl.getComparaciones()
            inserciones_bst = bst.getComparaciones()
            avl.reiniciarComparaciones()
            bst.reiniciarComparaciones()
            busquedas = []
            for clave in claves:
                _, avl_visitados = avl.buscarConConteo(clave)
                _, bst_visitados = bst.buscarConConteo(clave)
                busquedas.append({
                    "clave": list(clave),
                    "avl": {"comparaciones": avl_visitados},
                    "bst": {"comparaciones": bst_visitados},
                })

            resultados.append({
                "orden_insercion": orden,
                "cantidad_nodos": len(claves),
                "avl": self._metricas(avl, busquedas, "avl", inserciones_avl),
                "bst": self._metricas(bst, busquedas, "bst", inserciones_bst),
                "busquedas": busquedas,
                # Shape of both trees, so the interface can draw them side
                # by side (same format as /arbol/topologia). Read only.
                "topologia": {
                    "avl": topologia_anidada(avl),
                    "bst": topologia_anidada(bst),
                },
            })

        return {
            "cantidad_eventos": len(claves),
            "ordenes_evaluados": ordenes,
            "resultados": resultados,
        }

    @staticmethod
    def _ordenar(claves: list[tuple], orden: str) -> list[tuple]:
        if orden == "ascendente":
            return sorted(claves)
        if orden == "descendente":
            return sorted(claves, reverse=True)
        return list(claves)

    @staticmethod
    def _metricas(
        arbol, busquedas: list[dict], campo: str, comparaciones_insercion: int
    ) -> dict:
        conteos = [busqueda[campo]["comparaciones"] for busqueda in busquedas]
        return {
            "altura": arbol.altura(),
            "hojas": arbol.contarHojas(),
            "comparaciones_busqueda_total": sum(conteos),
            "comparaciones_busqueda_promedio": (
                sum(conteos) / len(conteos) if conteos else 0
            ),
            "comparaciones_busqueda_maximas": max(conteos, default=0),
            "comparaciones_insercion": comparaciones_insercion,
        }
