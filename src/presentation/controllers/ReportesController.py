from datetime import datetime
from typing import Any, Dict, Tuple

from flask import Blueprint, Flask, jsonify, request
from flask.wrappers import Response

from src.Models.Reportes import Reporte
from src.Models.Sismo import Sismo
from src.presentation.controllers.SismosController import _sismo_to_dict
from src.business.services.cola_reportes import ColaReportesService
from src.business.services.ModoAutomaticoService import ModoAutomaticoService
from src.business.services.reporte_service import (
    ReporteConflictoError,
    ReporteDesactualizadoError,
    ReporteIdentificadorRetiradoError,
    ReporteService,
    ReporteValidationError,
)
from src.business.services.SismosService import (
    SismoNotFoundError,
    SismoValidationError,
)



# ==============================================================================
# CONTROLADOR HTTP DE REPORTES SÍSMICOS
# ==============================================================================


class ReporteController:
    """Controlador HTTP para la gestión de reportes sísmicos enviados por estaciones.

    Ofrece endpoints para recepcionar reportes, gestionar la cola de procesamiento,
    descartar datos ruidosos y validar/emitir las actualizaciones de los eventos.
    """

    def __init__(
        self,
        reporte_service: ReporteService,
        cola_reportes: ColaReportesService,
        modo_automatico_service: ModoAutomaticoService,
    ) -> None:
        """Inicializa el controlador inyectando los servicios requeridos."""
        self.reporte_service = reporte_service
        self.cola_reportes = cola_reportes
        self.modo_automatico_service = modo_automatico_service

    @staticmethod
    def _serialize_reporte(reporte: Reporte) -> Dict[str, Any]:
        """Convierte una entidad Reporte en un diccionario serializable a JSON."""
        return {
            "sismo_id": reporte.sismo_id,
            "station_id": reporte.station_id,
            "magnitude": reporte.magnitude,
            "depth": reporte.depth,
            "epicenter_x": reporte.epicenter_x,
            "epicenter_y": reporte.epicenter_y,
            "timestamp": (
                reporte.timestamp.isoformat()
                if isinstance(reporte.timestamp, datetime)
                else reporte.timestamp
            ),
            "revision": reporte.revision,
        }

    # --------------------------------------------------------------------------
    # CREAR / ENCOLAR REPORTE
    # --------------------------------------------------------------------------

    def crear_reporte(self) -> Tuple[Response, int]:
        """Recepciona un nuevo reporte en formato JSON y lo añade a la cola."""
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "El cuerpo de la petición debe contener un JSON válido."}), 400

        try:
            timestamp = data.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            reporte = Reporte(
                sismo_id=data.get("sismo_id"),
                station_id=data.get("station_id"),
                magnitude=data.get("magnitude"),
                depth=data.get("depth"),
                epicenter_x=data.get("epicenter_x"),
                epicenter_y=data.get("epicenter_y"),
                timestamp=timestamp,
                revision=data.get("revision"),
            )

            self.cola_reportes.agregar_reporte(reporte)

            return jsonify({
                "mensaje": "Reporte agregado correctamente a la cola.",
                "reporte": self._serialize_reporte(reporte),
            }), 200

        except (ReporteValidationError, SismoValidationError, ValueError) as error:
            return jsonify({"error": str(error)}), 400

        except SismoNotFoundError as error:
            return jsonify({"error": str(error)}), 404

        except Exception as error:
            return jsonify({
                "error": "Error interno al agregar el reporte.",
                "detalle": str(error),
            }), 500

    # --------------------------------------------------------------------------
    # CONSULTAR COLA DE REPORTES
    # --------------------------------------------------------------------------

    def obtener_cola(self) -> Tuple[Response, int]:
        """Obtiene el listado actual de reportes pendientes en la cola."""
        try:
            cola = self.cola_reportes.obtener_cola()
            return jsonify({
                "cola": [self._serialize_reporte(reporte) for reporte in cola]
            }), 200

        except Exception as error:
            return jsonify({
                "error": "Error al consultar la cola de reportes.",
                "detalle": str(error),
            }), 500

    # --------------------------------------------------------------------------
    # DESCARTAR REPORTE COMO RUIDO
    # --------------------------------------------------------------------------

    def descartar_ruido(self) -> Tuple[Response, int]:
        """Elimina y descarta el reporte al frente de la cola por considerarse ruido."""
        try:
            if self.cola_reportes.esta_vacia():
                return jsonify({"error": "No hay reportes pendientes en la cola."}), 404

            reporte = self.cola_reportes.descartar_reporte()

            return jsonify({
                "mensaje": "Reporte descartado como ruido.",
                "decision": "ruido",
                "reporte": self._serialize_reporte(reporte),
            }), 200

        except Exception as error:
            return jsonify({
                "error": "No se pudo descartar el reporte.",
                "detalle": str(error),
            }), 500

    # --------------------------------------------------------------------------
    # VALIDAR Y EMITIR REPORTE
    # --------------------------------------------------------------------------

    def validar_y_emitir(self) -> Tuple[Response, int]:
        """Procesa y valida el reporte al frente de la cola, aplicando cambios al sismo."""
        try:
            if self.cola_reportes.esta_vacia():
                return jsonify({"error": "No hay reportes pendientes en la cola."}), 404

            reporte = self.cola_reportes.obtener_frente()
            resultado = self.reporte_service.procesar_reporte(reporte=reporte)

            # Confirmación o Corrección exitosa: Remover de la cola.
            self.cola_reportes.obtener_siguiente()
            sismo = self.reporte_service.sismo_service.get_by_id(reporte.sismo_id)

            return jsonify({
                "mensaje": "Reporte validado y emitido correctamente.",
                "decision": resultado.get("decision", "procesado"),
                "detalle_decision": resultado.get("mensaje", "Reporte procesado correctamente."),
                "reporte": {
                    "sismo_id": reporte.sismo_id,
                    "station_id": reporte.station_id,
                    "revision": reporte.revision,
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
                    "reporting_stations": list(sismo.reporting_stations),
                    "status": sismo.status.value,
                    "prioridad": sismo.prioridad,
                    "clave": list(sismo.clave) if sismo.clave else None,
                },
            }), 200

        except ReporteDesactualizadoError as error:
            self.cola_reportes.descartar_reporte()
            return jsonify({
                "mensaje": "El reporte fue rechazado.",
                "decision": "reporte_antiguo",
                "detalle_decision": str(error),
            }), 409

        except ReporteConflictoError as error:
            self.cola_reportes.descartar_reporte()
            return jsonify({
                "mensaje": "El reporte fue rechazado.",
                "decision": "conflicto",
                "detalle_decision": str(error),
            }), 409

        except ReporteIdentificadorRetiradoError as error:

            self.cola_reportes.descartar_reporte()
            return jsonify({
                "mensaje": "El reporte fue rechazado.",
                "decision": "identificador_retirado",
                "detalle_decision": str(error),
            }), 409

        except (ReporteValidationError, SismoValidationError, ValueError) as error:

            self.cola_reportes.descartar_reporte()
            return jsonify({
                "mensaje": "El reporte fue rechazado por datos inválidos.",
                "decision": "datos_invalidos",
                "detalle_decision": str(error),
            }), 400

        except SismoNotFoundError as error:
            return jsonify({"error": str(error)}), 404

        except Exception as error:
            return jsonify({
                "error": "No se pudo validar y emitir el reporte.",
                "detalle": str(error),
            }), 500

    # --------------------------------------------------------------------------
    # PROCESAMIENTO AUTOMÁTICO
    # --------------------------------------------------------------------------

    def procesar_automaticamente(self) -> Tuple[Response, int]:
        """Procesa automáticamente un único reporte de la cola."""
        try:
            resultado = self.modo_automatico_service.procesar_siguiente()
            if resultado.get("decision") == "cola_vacia":
                return jsonify(resultado), 404

            if isinstance(resultado.get("resultado"), Sismo):
                resultado["resultado"] = _sismo_to_dict(resultado["resultado"])

            return jsonify(resultado), 200

        except Exception as error:
            return jsonify({
                "error": "No se pudo procesar automáticamente el reporte.",
                "detalle": str(error),
            }), 500


def register_reporte_routes(
    app: Flask,
    reporte_service: ReporteService,
    cola_reportes: ColaReportesService,
    modo_automatico_service: ModoAutomaticoService,
) -> None:
    """Asocia e inscribe las rutas del controlador de reportes en Flask."""

    reporte_controller = Blueprint(
        "reporte_controller",
        __name__,
        url_prefix="/reportes",
    )

    controller = ReporteController(
        reporte_service=reporte_service,
        cola_reportes=cola_reportes,
        modo_automatico_service=modo_automatico_service,
    )

    reporte_controller.add_url_rule(
        "",
        view_func=controller.crear_reporte,
        methods=["POST"],
    )
    reporte_controller.add_url_rule(
        "/cola",
        view_func=controller.obtener_cola,
        methods=["GET"],
    )
    reporte_controller.add_url_rule(
        "/cola/descartar",
        view_func=controller.descartar_ruido,
        methods=["POST"],
    )
    reporte_controller.add_url_rule(
        "/cola/validar",
        view_func=controller.validar_y_emitir,
        methods=["POST"],
    )
    reporte_controller.add_url_rule(
        "/cola/automatico",
        view_func=controller.procesar_automaticamente,
        methods=["POST"],
    )

    app.register_blueprint(reporte_controller)