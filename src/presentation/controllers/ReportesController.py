
from datetime import datetime

from flask import Blueprint, jsonify, request

from src.Models.Reportes import Reporte

from src.business.services.reporte_service import (
    ReporteService,
    ReporteValidationError
)

from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoValidationError
)


reporte_controller = Blueprint(
    "reporte_controller",
    __name__,
    url_prefix="/reportes"
)


class ReporteController:
    """
    Controller HTTP para la gestión de reportes sísmicos.

    Responsabilidades:
        - Recibir peticiones HTTP.
        - Validar la estructura básica de la petición.
        - Convertir los datos recibidos al modelo Reporte.
        - Delegar el procesamiento al ReporteService.
        - Construir respuestas HTTP.

    No contiene reglas de negocio.
    """

    def __init__(
        self,
        reporte_service: ReporteService
    ):
        self.reporte_service = reporte_service

    # ------------------------------------------------------------------
    # CREAR / PROCESAR REPORTE
    # ------------------------------------------------------------------

    def crear_reporte(self):
        """
        Recibe y procesa un reporte realizado por una estación.

        POST /reportes
        """

        data = request.get_json(
            silent=True
        )

        if not data:
            return jsonify({
                "error": (
                    "El cuerpo de la petición debe contener "
                    "un JSON válido."
                )
            }), 400

        try:

            # ----------------------------------------------------------
            # Convertir timestamp
            # ----------------------------------------------------------

            timestamp = data.get(
                "timestamp"
            )

            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(
                    timestamp
                )

            # ----------------------------------------------------------
            # Crear modelo Reporte
            # ----------------------------------------------------------

            reporte = Reporte(
                sismo_id=data.get(
                    "sismo_id"
                ),

                station_id=data.get(
                    "station_id"
                ),

                magnitude=data.get(
                    "magnitude"
                ),

                depth=data.get(
                    "depth"
                ),

                epicenter_x=data.get(
                    "epicenter_x"
                ),

                epicenter_y=data.get(
                    "epicenter_y"
                ),

                timestamp=timestamp
            )

            # ----------------------------------------------------------
            # Procesar reporte
            #
            # ReporteService devuelve solamente el Sismo actualizado.
            # ----------------------------------------------------------

            sismo = self.reporte_service.procesar_reporte(
                reporte=reporte
            )

            # ----------------------------------------------------------
            # Respuesta
            # ----------------------------------------------------------

            return jsonify({

                "mensaje": (
                    "Reporte procesado correctamente."
                ),

                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id
                },

                "sismo": {

                    "id": sismo.id,

                    "formatted_id": (
                        sismo.formatted_id
                    ),

                    "magnitude": (
                        sismo.magnitude
                    ),

                    "depth": (
                        sismo.depth
                    ),

                    "epicenter": {
                        "longitude": (
                            sismo.epicenter_x
                        ),
                        "latitude": (
                            sismo.epicenter_y
                        )
                    },

                    "timestamp": (
                        sismo.timestamp.isoformat()
                    ),

                    "revision": (
                        sismo.revision
                    ),

                    "reporting_stations": list(
                        sismo.reporting_stations
                    ),

                    "status": (
                        sismo.status.value
                    ),

                    "prioridad": (
                        sismo.prioridad
                    ),

                    "clave": (
                        list(sismo.clave)
                        if sismo.clave
                        else None
                    )
                }

            }), 200

        # --------------------------------------------------------------
        # ERRORES DE VALIDACIÓN DEL REPORTE
        # --------------------------------------------------------------

        except ReporteValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400

        # --------------------------------------------------------------
        # ERRORES DE VALIDACIÓN DEL SISMO
        # --------------------------------------------------------------

        except SismoValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400

        # --------------------------------------------------------------
        # SISMO NO ENCONTRADO
        # --------------------------------------------------------------

        except SismoNotFoundError as error:

            return jsonify({
                "error": str(error)
            }), 404

        # --------------------------------------------------------------
        # OTROS ERRORES DE VALOR
        # --------------------------------------------------------------

        except ValueError as error:

            return jsonify({
                "error": str(error)
            }), 400

        # --------------------------------------------------------------
        # ERROR INTERNO
        # --------------------------------------------------------------

        except Exception as error:

            return jsonify({
                "error": (
                    "Error interno al procesar el reporte."
                ),
                "detalle": str(error)
            }), 500


# ----------------------------------------------------------------------
# REGISTRO DE RUTA
# ----------------------------------------------------------------------

def register_reporte_routes(
    app,
    reporte_service: ReporteService
):
    """
    Registra las rutas del controller de reportes.
    """

    controller = ReporteController(
        reporte_service
    )

    reporte_controller.add_url_rule(
        "",
        view_func=controller.crear_reporte,
        methods=["POST"]
    )

    app.register_blueprint(
        reporte_controller
    )

