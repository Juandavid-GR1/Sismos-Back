import re


class VersionesService:
    """Coordinates named persistent snapshots with complete state restore."""

    _NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")

    def __init__(self, estado_service, repository):
        self.estado_service = estado_service
        self.repository = repository

    def validar_nombre(self, nombre):
        if not isinstance(nombre, str) or not self._NOMBRE_VALIDO.fullmatch(nombre):
            raise ValueError(
                "El nombre debe tener entre 1 y 80 caracteres y solo usar "
                "letras, números, punto, guion o guion bajo."
            )
        return nombre

    def guardar(self, nombre: str) -> dict:
        return self.repository.guardar(
            self.validar_nombre(nombre),
            self.estado_service.capturar(),
        )

    def listar(self) -> list[dict]:
        return self.repository.listar()

    def obtener(self, nombre: str) -> dict:
        nombre = self.validar_nombre(nombre)
        version = self.repository.obtener(nombre)
        if version is None:
            raise KeyError(f"No existe la versión '{nombre}'.")
        estado = version["estado"]
        return {
            "nombre": version["nombre"],
            "fecha": version["fecha"],
            "resumen": {
                "eventos_activos": len(estado.get("sismos", [])),
                "eventos_historico": len(estado.get("historico", [])),
                "eventos_retirados": len(estado.get("eliminados", [])),
                "reportes_en_cola": len(estado.get("cola", [])),
                "modo_estres": estado.get("arbol", {}).get("modoEstres", False),
            },
        }

    def restaurar(self, nombre: str) -> dict:
        nombre = self.validar_nombre(nombre)
        version = self.repository.obtener(nombre)
        if version is None:
            raise KeyError(f"No existe la versión '{nombre}'.")
        self.estado_service.restaurar(version["estado"])
        return {
            "nombre": nombre,
            "fecha": version["fecha"],
            "mensaje": "Versión restaurada correctamente.",
        }
