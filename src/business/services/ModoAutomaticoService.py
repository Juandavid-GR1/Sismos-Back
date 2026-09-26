
from typing import Any

from src.business.services.cola_reportes import ColaReportesService
from src.business.services.reporte_service import (
    ReporteService,
    ReporteDesactualizadoError,
    ReporteConflictoError,
)


class ModoAutomaticoService:
    """
    Servicio encargado de procesar automáticamente los reportes
    que se encuentran en la cola.

    El intervalo de ejecución NO se controla aquí.
    El Frontend será quien determine cada cuánto solicita
    una nueva revisión.

    Este servicio únicamente procesa un reporte por solicitud.
    """

    def __init__(
        self,
        cola_reportes: ColaReportesService,
        reporte_service: ReporteService,
    ) -> None:

        self.cola_reportes = cola_reportes
        self.reporte_service = reporte_service

    def procesar_siguiente(self) -> dict[str, Any]:
        """
        Procesa el siguiente reporte disponible en la cola.

        Returns:
            dict[str, Any]: Resultado del procesamiento automático.
        """

        # Verificar si existen reportes pendientes
        if self.cola_reportes.esta_vacia():
            return {
                "procesado": False,
                "decision": "cola_vacia",
                "mensaje": "No hay reportes pendientes para procesar.",
            }

        # Obtener el reporte que está al frente.
        # Todavía no se elimina de la cola.
        reporte = self.cola_reportes.obtener_frente()

        try:
            # Procesar el reporte utilizando toda la lógica
            # existente de ReporteService.
            resultado = self.reporte_service.procesar_reporte(
                reporte=reporte
            )

            # Solo se elimina de la cola cuando el procesamiento
            # terminó correctamente.
            self.cola_reportes.obtener_siguiente()

            return {
                "procesado": True,
                "decision": resultado.get(
                    "decision",
                    "procesado",
                ),
                "mensaje": resultado.get(
                    "mensaje",
                    "Reporte procesado correctamente.",
                ),
                "resultado": resultado.get(
                    "resultado"
                ),
                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                    "revision": reporte.revision,
                },
            }

        except ReporteDesactualizadoError as error:

            # Un reporte antiguo no debe permanecer en la cola.
            self.cola_reportes.descartar_reporte()

            return {
                "procesado": True,
                "decision": "reporte_antiguo",
                "mensaje": "El reporte fue rechazado por estar desactualizado.",
                "detalle_decision": str(error),
                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                    "revision": reporte.revision,
                },
            }

        except ReporteConflictoError as error:

            # Un reporte conflictivo tampoco debe permanecer
            # bloqueando la cola.
            self.cola_reportes.descartar_reporte()

            return {
                "procesado": True,
                "decision": "conflicto",
                "mensaje": "El reporte fue rechazado por conflicto.",
                "detalle_decision": str(error),
                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                    "revision": reporte.revision,
                },
            }

