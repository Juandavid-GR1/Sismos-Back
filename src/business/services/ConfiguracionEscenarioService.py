import json
import os


class ConfiguracionEscenarioService:
    """Persists the limits that affect derived AVL and archive indicators."""

    def __init__(self, avl_service, json_file="data/configuracion_escenario.json"):
        self.avl_service = avl_service
        self.json_file = json_file
        self.limite_profundidad = 3
        self.antiguedad_archivo_horas = 72.0
        self._cargar()
        self.actualizar_marcas()

    def _cargar(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            limite = datos.get("limite_profundidad", 3)
            antiguedad = datos.get("antiguedad_archivo_horas", 72)
            self._validar(limite, antiguedad)
            self.limite_profundidad = int(limite)
            self.antiguedad_archivo_horas = float(antiguedad)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self._persistir()

    @staticmethod
    def _validar(limite, antiguedad):
        if isinstance(limite, bool) or int(limite) != float(limite) or int(limite) < 0:
            raise ValueError("L debe ser un entero no negativo.")
        if float(antiguedad) <= 0:
            raise ValueError("T debe ser un número positivo.")

    def _persistir(self):
        carpeta = os.path.dirname(self.json_file)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        temporal = f"{self.json_file}.tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(self.exportar(), archivo, indent=2, ensure_ascii=False)
        os.replace(temporal, self.json_file)

    def exportar(self):
        return {
            "limite_profundidad": self.limite_profundidad,
            "antiguedad_archivo_horas": self.antiguedad_archivo_horas,
        }

    def reemplazar(self, estado):
        estado = estado or {}
        limite = estado.get("limite_profundidad", 3)
        antiguedad = estado.get("antiguedad_archivo_horas", 72)
        self._validar(limite, antiguedad)
        self.limite_profundidad = int(limite)
        self.antiguedad_archivo_horas = float(antiguedad)
        self._persistir()
        self.actualizar_marcas()

    def configurar(self, limite=None, antiguedad=None):
        nuevo_limite = self.limite_profundidad if limite is None else limite
        nueva_antiguedad = (
            self.antiguedad_archivo_horas if antiguedad is None else antiguedad
        )
        self._validar(nuevo_limite, nueva_antiguedad)
        self.limite_profundidad = int(nuevo_limite)
        self.antiguedad_archivo_horas = float(nueva_antiguedad)
        self._persistir()
        self.actualizar_marcas()
        return self.exportar()

    def actualizar_marcas(self):
        self.avl_service.actualizar_marcas_acceso_costoso(
            self.limite_profundidad
        )
