from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.Models.Reportes import Reporte
from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService
from src.business.services.SismosService import SismoService
from src.business.services.ZonaService import ZonaService

# ==============================================================================
# EXCEPCIONES DOMINIO DE REPORTES
# ==============================================================================


class ReporteValidationError(ValueError):
    """Excepción lanzada cuando los datos de un reporte no cumplen la validación sintáctica o de rango."""

    pass


class ReporteDesactualizadoError(ValueError):
    """Excepción lanzada cuando la revisión del reporte es menor a la revisión actual del sismo."""

    pass


class ReporteConflictoError(ValueError):
    """Excepción lanzada cuando un reporte de la misma revisión contiene datos discrepantes con el sismo."""

    pass


# ==============================================================================
# SERVICIO DE PROCESAMIENTO DE REPORTES
# ==============================================================================


class ReporteService:
    """Servicio encargado de validar, comparar y procesar los reportes de eventos sísmicos.

    Aplica la lógica de resolución de revisiones para determinar si un reporte
    constituye una confirmación, un conflicto o una corrección/actualización.

    Attributes:
        sismo_service (SismoService): Servicio para operaciones sobre el modelo de sismos.
        priority_key_service (PriorityKeyService): Servicio para cálculo de prioridades y claves.
        zona_service (ZonaService): Servicio para consultas de geofencing y zonas pobladas.
    """

    def __init__(
        self,
        sismo_service: SismoService,
        priority_key_service: PriorityKeyService,
        zona_service: ZonaService,
    ) -> None:
        """Inicializa las dependencias necesarias para la gestión de reportes."""
        self.sismo_service = sismo_service
        self.priority_key_service = priority_key_service
        self.zona_service = zona_service

    # --------------------------------------------------------------------------
    # PROCESAMIENTO PRINCIPAL
    # --------------------------------------------------------------------------

    def procesar_reporte(self, reporte: Reporte) -> Dict[str, Any]:
        """Procesa un reporte entrante aplicando la matriz de reglas de revisión sísmica.

        Reglas de Revisión:
            1. `reporte.revision < sismo.revision`:
                Se descarta por estar obsoleto/desactualizado.

            2. `reporte.revision == sismo.revision`:
                - Si coinciden los datos: Se procesa como Confirmación.
                - Si difieren los datos: Eleva ReporteConflictoError.

            3. `reporte.revision > sismo.revision`:
                Se procesa como Corrección/Nueva versión recalculando prioridad.

        Raises:
            ReporteValidationError: Si el reporte no cumple con las restricciones sintácticas/tipo.
            ReporteDesactualizadoError: Si el reporte hace referencia a una revisión obsoleta.
            ReporteConflictoError: Si el reporte entra en contradicción en la revisión actual.
        """
        self.validar_reporte(reporte)
        sismo = self.sismo_service.get_by_id(reporte.sismo_id)

        # Caso 1: Reporte desactualizado
        if reporte.revision < sismo.revision:
            raise ReporteDesactualizadoError(
                f"El reporte pertenece a la revisión {reporte.revision}, "
                f"pero el sismo ya se encuentra en la revisión {sismo.revision}."
            )

        # Caso 2: Misma revisión
        if reporte.revision == sismo.revision:
            if not self.es_confirmacion(sismo, reporte):
                raise ReporteConflictoError(
                    f"El reporte de la revisión {reporte.revision} "
                    f"contiene datos diferentes a los del sismo."
                )

            prioridad, clave = None, None
            if sismo.prioridad is None or sismo.clave is None:
                prioridad, clave = self._calcular_prioridad_y_clave(reporte)

            resultado = self.procesar_confirmacion(
                reporte=reporte,
                prioridad=prioridad,
                clave=clave,
            )

            return {
                "decision": "confirmacion",
                "mensaje": "El reporte confirma la información existente.",
                "resultado": resultado,
            }

        # Caso 3: Nueva revisión (reporte.revision > sismo.revision)
        prioridad, clave = self._calcular_prioridad_y_clave(reporte)
        resultado = self.procesar_correccion(
            reporte=reporte,
            prioridad=prioridad,
            clave=clave,
        )

        return {
            "decision": "correccion",
            "mensaje": "Se aplicó una corrección al evento.",
            "resultado": resultado,
        }

    # --------------------------------------------------------------------------
    # MÉTODOS AUXILIARES Y DE CÁLCULO
    # --------------------------------------------------------------------------

    def _calcular_prioridad_y_clave(
        self, reporte: Reporte
    ) -> Tuple[int, Tuple[int, float, int]]:
        """Calcula la zona poblada, prioridad y clave única para un reporte dado."""
        zona_poblada = self.zona_service.punto_en_zona(
            longitud=reporte.epicenter_x,
            latitud=reporte.epicenter_y,
        )

        prioridad = self.priority_key_service.calcular_prioridad(
            magnitude=reporte.magnitude,
            depth=reporte.depth,
            zona_poblada=zona_poblada,
        )

        clave = self.priority_key_service.generar_clave(
            prioridad=prioridad,
            magnitude=reporte.magnitude,
            sismo_id=reporte.sismo_id,
        )

        return prioridad, clave

    def es_confirmacion(self, sismo: Any, reporte: Reporte) -> bool:
        """Determina si un reporte coincide exactamente con la información actual del sismo."""
        return (
            sismo.magnitude == reporte.magnitude
            and sismo.depth == reporte.depth
            and sismo.epicenter_x == reporte.epicenter_x
            and sismo.epicenter_y == reporte.epicenter_y
        )

    def es_correccion(self, sismo: Any, reporte: Reporte) -> bool:
        """Evalúa si los datos del reporte difieren de los almacenados en el sismo actual."""
        return not self.es_confirmacion(sismo, reporte)

    def procesar_confirmacion(
        self,
        reporte: Reporte,
        prioridad: Optional[int] = None,
        clave: Optional[Tuple[int, float, int]] = None,
    ) -> Any:
        """Registra una estación como confirmante dentro del consenso del sismo."""
        return self.sismo_service.add_consensus_report(
            sismo_id=reporte.sismo_id,
            station_id=reporte.station_id,
            prioridad=prioridad,
            clave=clave,
        )

    def procesar_correccion(
        self,
        reporte: Reporte,
        prioridad: int,
        clave: Tuple[int, float, int],
    ) -> Any:
        """Aplica la actualización de parámetros e incremento de versión al sismo."""
        return self.sismo_service.apply_correction(
            sismo_id=reporte.sismo_id,
            station_id=reporte.station_id,
            magnitude=reporte.magnitude,
            depth=reporte.depth,
            epicenter_x=reporte.epicenter_x,
            epicenter_y=reporte.epicenter_y,
            prioridad=prioridad,
            clave=clave,
            revision=reporte.revision,
        )

    # --------------------------------------------------------------------------
    # VALIDACIÓN SINTÁCTICA Y DE RANGOS
    # --------------------------------------------------------------------------

    def validar_reporte(self, reporte: Reporte) -> None:
        """Valida la existencia, tipos y rangos numéricos aceptables de los atributos del reporte."""
        if reporte is None:
            raise ReporteValidationError("El reporte no puede ser None.")

        if not isinstance(reporte, Reporte):
            raise ReporteValidationError("El objeto recibido debe ser un Reporte.")

        # Identificador del sismo
        if not isinstance(reporte.sismo_id, int) or reporte.sismo_id <= 0:
            raise ReporteValidationError("El sismo_id debe ser un entero positivo.")

        # Identificador de la estación
        if not isinstance(reporte.station_id, str) or not reporte.station_id.strip():
            raise ReporteValidationError("El station_id debe ser un texto no vacío.")

        # Número de revisión
        if not isinstance(reporte.revision, int) or reporte.revision <= 0:
            raise ReporteValidationError("La revisión debe ser un entero positivo.")

        # Magnitud (Mw / ML)
        if not isinstance(reporte.magnitude, (int, float)) or not (-2.0 <= reporte.magnitude <= 10.0):
            raise ReporteValidationError("La magnitud debe ser numérica entre -2.0 y 10.0.")

        # Profundidad (km)
        if not isinstance(reporte.depth, (int, float)) or not (0.0 <= reporte.depth <= 700.0):
            raise ReporteValidationError("La profundidad debe ser numérica entre 0.0 y 700.0 km.")

        # Coordenadas: Longitud (X)
        if not isinstance(reporte.epicenter_x, (int, float)) or not (-180.0 <= reporte.epicenter_x <= 180.0):
            raise ReporteValidationError("La longitud debe estar entre -180.0 y 180.0 grados.")

        # Coordenadas: Latitud (Y)
        if not isinstance(reporte.epicenter_y, (int, float)) or not (-90.0 <= reporte.epicenter_y <= 90.0):
            raise ReporteValidationError("La latitud debe estar entre -90.0 y 90.0 grados.")

        # Marca temporal
        if not isinstance(reporte.timestamp, datetime):
            raise ReporteValidationError("El timestamp debe ser una instancia de datetime.")