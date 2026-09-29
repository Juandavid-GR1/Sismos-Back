"""
EliminadosService

Registro de identificadores RETIRADOS (sección 6 del enunciado):
"Un identificador eliminado no puede reutilizarse ni reactivarse
mediante un reporte posterior. El evento solo puede recuperarse al
deshacer la eliminación... Un identificador eliminado se conserva
como retirado: sus reportes posteriores se rechazan hasta deshacer
esa eliminación."

Esto es DISTINTO de "archivado" (sección 10, todavía no construido):
un evento archivado SÍ puede reactivarse con una revisión mayor; un
evento eliminado individualmente NO, hasta que exista deshacer
(sección 13, también pendiente).

Por ahora vive en memoria, igual que AvlService -- cuando se
construya la persistencia (sección 12), este set debe formar parte
del "guardado estructural" ("identificadores retirados").
"""


class EliminadosService:

    def __init__(self):
        self._retirados = set()

    def marcar_retirado(self, sismo_id: int) -> None:
        self._retirados.add(sismo_id)

    def esta_retirado(self, sismo_id: int) -> bool:
        return sismo_id in self._retirados

    def todos(self) -> set:
        """Copia del conjunto completo -- para exportación futura."""
        return set(self._retirados)

    def cantidad(self) -> int:
        return len(self._retirados)

    def reemplazar(self, ids) -> None:
        """Restores the whole set (undo / versions)."""
        self._retirados = set(int(i) for i in ids)