
from datetime import datetime

from src.Models.Reportes import Reporte

from src.business.services.SismosService import (
    SismoService
)

from src.business.services.ZonaService import (
    ZonaService
)

from src.business.algortimos.sismos.Priority_Key_sismo import (
    PriorityKeyService
)


class ReporteValidationError(ValueError):
    """Excepción para errores de validación de reportes."""
    pass


class ReporteService:
    """
    Servicio encargado de procesar los reportes realizados
    por las estaciones sobre sismos existentes.

    Responsabilidades:
        - Validar los datos del reporte.
        - Obtener el sismo asociado mediante su ID.
        - Determinar automáticamente si el epicentro
          pertenece a una zona poblada.
        - Calcular la prioridad del reporte.
        - Generar la clave (P, M, I).
        - Determinar si el reporte es una confirmación
          o una corrección.
        - Delegar la modificación del sismo al SismoService.

    Este servicio NO:
        - crea sismos;
        - busca sismos por distancia o tiempo;
        - administra directamente el AVL;
        - administra directamente la persistencia.
    """

    def __init__(
        self,
        sismo_service: SismoService,
        priority_key_service: PriorityKeyService,
        zona_service: ZonaService
    ):
        self.sismo_service = sismo_service
        self.priority_key_service = priority_key_service
        self.zona_service = zona_service

    # ------------------------------------------------------------------
    # PROCESAMIENTO PRINCIPAL
    # ------------------------------------------------------------------

    def procesar_reporte(
        self,
        reporte: Reporte
    ):
        """
        Procesa un reporte que ya está asociado a un sismo existente.

        La zona poblada se determina automáticamente utilizando
        las coordenadas del epicentro del reporte.

        Flujo:
            1. Validar el reporte.
            2. Obtener el sismo mediante sismo_id.
            3. Determinar si el epicentro está en una zona poblada.
            4. Calcular la prioridad.
            5. Generar la clave (P, M, I).
            6. Determinar si es confirmación o corrección.
            7. Delegar la actualización al SismoService.
            8. Retornar el sismo actualizado.

        La prioridad y la clave se calculan una sola vez
        y posteriormente se actualizan en el Sismo.
        """

        # --------------------------------------------------------------
        # Validar reporte
        # --------------------------------------------------------------

        self.validar_reporte(
            reporte
        )

        # --------------------------------------------------------------
        # Obtener el sismo existente
        # --------------------------------------------------------------

        sismo = self.sismo_service.get_by_id(
            reporte.sismo_id
        )

        # --------------------------------------------------------------
        # Determinar automáticamente la zona
        # --------------------------------------------------------------

        zona_poblada = self.zona_service.punto_en_zona(
            longitud=reporte.epicenter_x,
            latitud=reporte.epicenter_y
        )

        # --------------------------------------------------------------
        # Calcular prioridad
        # --------------------------------------------------------------

        prioridad = self.priority_key_service.calcular_prioridad(
            magnitude=reporte.magnitude,
            depth=reporte.depth,
            zona_poblada=zona_poblada
        )

        # --------------------------------------------------------------
        # Generar clave (P, M, I)
        #
        # Se calcula UNA SOLA VEZ.
        # --------------------------------------------------------------

        clave = self.priority_key_service.generar_clave(
            prioridad=prioridad,
            magnitude=reporte.magnitude,
            sismo_id=sismo.id
        )

        # --------------------------------------------------------------
        # Determinar si es confirmación o corrección
        # --------------------------------------------------------------

        if self.es_confirmacion(
            sismo,
            reporte
        ):
            sismo = self.procesar_confirmacion(
                reporte=reporte,
                prioridad=prioridad,
                clave=clave
            )

        else:
            sismo = self.procesar_correccion(
                reporte=reporte,
                prioridad=prioridad,
                clave=clave
            )

        # --------------------------------------------------------------
        # Retornar únicamente el sismo actualizado
        # --------------------------------------------------------------

        return sismo

    # ------------------------------------------------------------------
    # VALIDACIÓN
    # ------------------------------------------------------------------

    def validar_reporte(
        self,
        reporte: Reporte
    ) -> None:
        """
        Valida los datos básicos de un reporte.
        """

        # --------------------------------------------------------------
        # Reporte
        # --------------------------------------------------------------

        if reporte is None:
            raise ReporteValidationError(
                "El reporte no puede ser None."
            )

        if not isinstance(reporte, Reporte):
            raise ReporteValidationError(
                "El objeto recibido debe ser un Reporte."
            )

        # --------------------------------------------------------------
        # Sismo
        # --------------------------------------------------------------

        if reporte.sismo_id is None:
            raise ReporteValidationError(
                "El reporte debe tener un sismo asociado."
            )

        if not isinstance(
            reporte.sismo_id,
            int
        ):
            raise ReporteValidationError(
                "El sismo_id debe ser un número entero."
            )

        if reporte.sismo_id <= 0:
            raise ReporteValidationError(
                "El sismo_id debe ser mayor que cero."
            )

        # --------------------------------------------------------------
        # Estación
        # --------------------------------------------------------------

        if not isinstance(
            reporte.station_id,
            str
        ):
            raise ReporteValidationError(
                "El station_id debe ser texto."
            )

        if not reporte.station_id.strip():
            raise ReporteValidationError(
                "El station_id no puede estar vacío."
            )

        # --------------------------------------------------------------
        # Magnitud
        # --------------------------------------------------------------

        if not isinstance(
            reporte.magnitude,
            (int, float)
        ):
            raise ReporteValidationError(
                "La magnitud debe ser numérica."
            )

        if not -2.0 <= reporte.magnitude <= 10.0:
            raise ReporteValidationError(
                "La magnitud debe estar entre -2.0 y 10.0."
            )

        # --------------------------------------------------------------
        # Profundidad
        # --------------------------------------------------------------

        if not isinstance(
            reporte.depth,
            (int, float)
        ):
            raise ReporteValidationError(
                "La profundidad debe ser numérica."
            )

        if not 0.0 <= reporte.depth <= 700.0:
            raise ReporteValidationError(
                "La profundidad debe estar entre 0.0 y 700.0 km."
            )

        # --------------------------------------------------------------
        # Longitud (X)
        # Rango mundial: -180° a 180°
        # --------------------------------------------------------------

        if not isinstance(
            reporte.epicenter_x,
            (int, float)
        ):
            raise ReporteValidationError(
                "La longitud debe ser numérica."
            )

        if not -180.0 <= reporte.epicenter_x <= 180.0:
            raise ReporteValidationError(
                "La longitud debe estar entre -180.0 y 180.0 grados."
            )

        # --------------------------------------------------------------
        # Latitud (Y)
        # Rango mundial: -90° a 90°
        # --------------------------------------------------------------

        if not isinstance(
            reporte.epicenter_y,
            (int, float)
        ):
            raise ReporteValidationError(
                "La latitud debe ser numérica."
            )

        if not -90.0 <= reporte.epicenter_y <= 90.0:
            raise ReporteValidationError(
                "La latitud debe estar entre -90.0 y 90.0 grados."
            )

        # --------------------------------------------------------------
        # Timestamp
        # --------------------------------------------------------------

        if not isinstance(
            reporte.timestamp,
            datetime
        ):
            raise ReporteValidationError(
                "El timestamp debe ser una instancia de datetime."
            )

    # ------------------------------------------------------------------
    # CONFIRMACIÓN
    # ------------------------------------------------------------------

    def es_confirmacion(
        self,
        sismo,
        reporte: Reporte
    ) -> bool:
        """
        Determina si el reporte mantiene los mismos parámetros
        físicos del sismo actual.

        Si todos los parámetros físicos coinciden,
        el reporte se considera una confirmación.
        """

        return (
            sismo.magnitude == reporte.magnitude
            and
            sismo.depth == reporte.depth
            and
            sismo.epicenter_x == reporte.epicenter_x
            and
            sismo.epicenter_y == reporte.epicenter_y
        )

    def procesar_confirmacion(
        self,
        reporte: Reporte,
        prioridad: int,
        clave: tuple[int, float, int]
    ):
        """
        Procesa un reporte cuyos datos físicos coinciden
        con los datos actuales del sismo.

        La prioridad y la clave ya fueron calculadas
        previamente por procesar_reporte().

        El SismoService se encarga de:
            - actualizar prioridad;
            - actualizar clave;
            - agregar la estación al conjunto;
            - incrementar la revisión;
            - guardar el sismo.
        """

        return self.sismo_service.add_consensus_report(
            sismo_id=reporte.sismo_id,
            station_id=reporte.station_id,
            prioridad=prioridad,
            clave=clave
        )

    # ------------------------------------------------------------------
    # CORRECCIÓN
    # ------------------------------------------------------------------

    def es_correccion(
        self,
        sismo,
        reporte: Reporte
    ) -> bool:
        """
        Determina si el reporte modifica algún parámetro físico
        del sismo.
        """

        return not self.es_confirmacion(
            sismo,
            reporte
        )

    def procesar_correccion(
        self,
        reporte: Reporte,
        prioridad: int,
        clave: tuple[int, float, int]
    ):
        """
        Procesa un reporte que modifica los parámetros físicos
        actuales del sismo.

        La prioridad y la clave ya fueron calculadas
        previamente por procesar_reporte().

        El SismoService se encarga de:
            - actualizar los datos físicos;
            - actualizar prioridad;
            - actualizar clave;
            - agregar la estación;
            - incrementar la revisión;
            - establecer el estado PENDIENTE;
            - guardar el sismo.
        """

        return self.sismo_service.apply_correction(
            sismo_id=reporte.sismo_id,
            station_id=reporte.station_id,
            magnitude=reporte.magnitude,
            depth=reporte.depth,
            epicenter_x=reporte.epicenter_x,
            epicenter_y=reporte.epicenter_y,
            prioridad=prioridad,
            clave=clave
        )
