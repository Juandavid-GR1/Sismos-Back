from datetime import datetime

from flask import Blueprint, jsonify, request

from src.business.services.cola_reportes import ColaReportesService

from src.business.services.reporte_service import (
    ReporteService,
    ReporteValidationError,
)

from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoValidationError,
)

from src.Models.Reportes import Reporte


reporte_controller = Blueprint(
    "reporte_controller",
    __name__,
    url_prefix="/reportes"
)


class ReporteController:

    def __init__(
        self,
        reporte_service: ReporteService,
        cola_reportes: ColaReportesService
    ):
        self.reporte_service = reporte_service
        self.cola_reportes = cola_reportes


    # ------------------------------------------------------------------
    # CREAR / PROCESAR REPORTE
    # ------------------------------------------------------------------

    def crear_reporte(self):

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "error": "El cuerpo de la petición debe contener un JSON válido."
            }), 400

        try:

            # ----------------------------------------------------------
            # Convertir timestamp
            # ----------------------------------------------------------

            timestamp = data.get("timestamp")

            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)


            # ----------------------------------------------------------
            # Crear modelo Reporte
            # ----------------------------------------------------------

            reporte = Reporte(
                sismo_id=data.get("sismo_id"),
                station_id=data.get("station_id"),
                magnitude=data.get("magnitude"),
                depth=data.get("depth"),
                epicenter_x=data.get("epicenter_x"),
                epicenter_y=data.get("epicenter_y"),
                timestamp=timestamp,
            )


            # ----------------------------------------------------------
            # AGREGAR REPORTE A LA COLA
            # ----------------------------------------------------------

            self.cola_reportes.agregar_reporte(reporte)


            # ----------------------------------------------------------
            # PROCESAR REPORTE
            # ----------------------------------------------------------

            sismo = self.reporte_service.procesar_reporte(
                reporte=reporte
            )


            # ----------------------------------------------------------
            # RESPUESTA
            # ----------------------------------------------------------

            return jsonify({

                "mensaje": "Reporte procesado correctamente.",

                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                },

                "sismo": {
                    "id": sismo.id,
                    "formatted_id": sismo.formatted_id,
                    "magnitude": sismo.magnitude,
                    "depth": sismo.depth,

                    "epicenter": {
                        "longitude": sismo.epicenter_x,
                        "latitude": sismo.epicenter_y,
                    },

                    "timestamp": sismo.timestamp.isoformat(),

                    "revision": sismo.revision,

                    "reporting_stations": list(
                        sismo.reporting_stations
                    ),

                    "status": sismo.status.value,

                    "prioridad": sismo.prioridad,

                    "clave": (
                        list(sismo.clave)
                        if sismo.clave
                        else None
                    ),
                },

            }), 200


        except ReporteValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except SismoValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except SismoNotFoundError as error:

            return jsonify({
                "error": str(error)
            }), 404


        except ValueError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except Exception as error:

            return jsonify({
                "error": "Error interno al procesar el reporte.",
                "detalle": str(error),
            }), 500


    # ------------------------------------------------------------------
    # OBTENER COLA DE REPORTES
    # ------------------------------------------------------------------

    def obtener_cola(self):

        try:

            cola = self.cola_reportes.obtener_cola()

            return jsonify({

                "cola": [

                    {
                        "sismo_id": reporte.sismo_id,
                        "station_id": reporte.station_id,
                        "magnitude": reporte.magnitude,
                        "depth": reporte.depth,
                        "epicenter_x": reporte.epicenter_x,
                        "epicenter_y": reporte.epicenter_y,
                        "timestamp": reporte.timestamp.isoformat(),
                    }

                    for reporte in cola

                ]

            }), 200


        except Exception as error:

            return jsonify({
                "error": "Error al consultar la cola de reportes.",
                "detalle": str(error),
            }), 500


    # ------------------------------------------------------------------
    # DESCARTAR REPORTE COMO RUIDO
    # ------------------------------------------------------------------

    def descartar_ruido(self):

        try:

            if self.cola_reportes.esta_vacia():

                return jsonify({
                    "error": "No hay reportes pendientes en la cola."
                }), 404


            reporte = self.cola_reportes.descartar_reporte()


            return jsonify({

                "mensaje": "Reporte descartado como ruido.",

                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                    "magnitude": reporte.magnitude,
                    "depth": reporte.depth,
                    "epicenter_x": reporte.epicenter_x,
                    "epicenter_y": reporte.epicenter_y,
                    "timestamp": reporte.timestamp.isoformat()
                }

            }), 200


        except Exception as error:

            return jsonify({

                "error": "No se pudo descartar el reporte.",

                "detalle": str(error)

            }), 500


    # ------------------------------------------------------------------
    # VALIDAR Y EMITIR
    # ------------------------------------------------------------------

    def validar_y_emitir(self):

        try:

            if self.cola_reportes.esta_vacia():

                return jsonify({
                    "error": "No hay reportes pendientes en la cola."
                }), 404


            reporte = self.cola_reportes.obtener_frente()


            # Procesar mediante el servicio existente
            sismo = self.reporte_service.procesar_reporte(
                reporte=reporte
            )


            # Solo se elimina de la cola después
            # de procesarlo correctamente
            self.cola_reportes.obtener_siguiente()


            return jsonify({

                "mensaje": "Reporte validado y emitido correctamente.",

                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                },

                "sismo": {
                    "id": sismo.id,
                    "formatted_id": sismo.formatted_id,
                    "magnitude": sismo.magnitude,
                    "depth": sismo.depth,

                    "epicenter": {
                        "longitude": sismo.epicenter_x,
                        "latitude": sismo.epicenter_y,
                    },

                    "timestamp": sismo.timestamp.isoformat(),

                    "revision": sismo.revision,

                    "reporting_stations": list(
                        sismo.reporting_stations
                    ),

                    "status": sismo.status.value,

                    "prioridad": sismo.prioridad,

                    "clave": (
                        list(sismo.clave)
                        if sismo.clave
                        else None
                    ),
                }

            }), 200


        except ReporteValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except SismoValidationError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except SismoNotFoundError as error:

            return jsonify({
                "error": str(error)
            }), 404


        except ValueError as error:

            return jsonify({
                "error": str(error)
            }), 400


        except Exception as error:

            return jsonify({

                "error": "No se pudo validar y emitir el reporte.",

                "detalle": str(error)

            }), 500



# ----------------------------------------------------------------------
# REGISTRO DE RUTAS
# ----------------------------------------------------------------------

def register_reporte_routes(
    app,
    reporte_service: ReporteService,
    cola_reportes: ColaReportesService
):

    controller = ReporteController(
        reporte_service,
        cola_reportes
    )


    # POST /reportes

    reporte_controller.add_url_rule(
        "",
        view_func=controller.crear_reporte,
        methods=["POST"]
    )


    # GET /reportes/cola

    reporte_controller.add_url_rule(
        "/cola",
        view_func=controller.obtener_cola,
        methods=["GET"]
    )


    # POST /reportes/cola/descartar

    reporte_controller.add_url_rule(
        "/cola/descartar",
        view_func=controller.descartar_ruido,
        methods=["POST"]
    )


    # POST /reportes/cola/validar

    reporte_controller.add_url_rule(
        "/cola/validar",
        view_func=controller.validar_y_emitir,
        methods=["POST"]
    )


    app.register_blueprint(reporte_controller)