
from datetime import datetime
from typing import Protocol, Optional, Any

from src.Models.Sismo import Sismo, StatusSismo

from src.business.algortimos.sismos.SismoValidationService import (
    SismoValidationService,
    SismoValidationError
)

from src.business.algortimos.sismos.SismoComparison import (
    SismoComparison
)


class SismoNotFoundError(KeyError):
    """Excepción lanzada cuando no se encuentra un evento sísmico."""
    pass


class ISismoRepository(Protocol):
    """Interfaz para abstraer la capa de persistencia."""

    def get_by_id(
        self,
        sismo_id: int
    ) -> Optional[Sismo]:
        ...

    def get_all(self) -> list[Sismo]:
        ...

    def save(
        self,
        sismo: Sismo
    ) -> Sismo:
        ...

    def delete(
        self,
        sismo_id: int
    ) -> bool:
        ...

    def generate_next_id(self) -> int:
        ...


class SismoService:
    """
    Capa de servicio para la entidad Sismo.

    Implementa las reglas de negocio, consenso de estaciones,
    control de revisiones, prioridades y claves.
    """

    def __init__(
        self,
        repository: ISismoRepository
    ):
        self.repository = repository

    # ------------------------------------------------------------------
    # CREAR EVENTO
    # ------------------------------------------------------------------

    def create_event(
        self,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
        initial_station_id: Optional[str] = None,
    ) -> Sismo:
        """
        Crea un nuevo evento sísmico.

        El sismo se crea inicialmente con:
            - revision = 0
            - reporting_stations = vacío
            - status = PENDIENTE
            - prioridad = None
            - clave = None

        La estación se registra posteriormente cuando un Reporte
        sea procesado mediante ReporteService.
        """

        SismoValidationService.validate_station_id(
            initial_station_id
        )

        sismo_id = self.repository.generate_next_id()

        SismoValidationService.validate_id(
            sismo_id
        )

        sismo = Sismo(
            id=sismo_id,

            magnitude=SismoValidationService.validate_magnitude(
                magnitude
            ),

            depth=SismoValidationService.validate_depth(
                depth
            ),

            epicenter_x=SismoValidationService.validate_epicenter_coord(
                epicenter_x,
                "epicenter_x"
            ),

            epicenter_y=SismoValidationService.validate_epicenter_coord(
                epicenter_y,
                "epicenter_y"
            ),

            timestamp=SismoValidationService.validate_timestamp(
                timestamp
            ),

            revision=0,
            reporting_stations=set(),
            prioridad=None,
            clave=None,
            status=StatusSismo.PENDIENTE,
        )

        return self.repository.save(
            sismo
        )

    # ------------------------------------------------------------------
    # CONSENSO / REPORTE CONFIRMATORIO
    # ------------------------------------------------------------------

    def add_consensus_report(
        self,
        sismo_id: int,
        station_id: str,
        prioridad: Optional[int] = None,
        clave: Optional[tuple[int, float, int]] = None
    ) -> Sismo:
        """
        Procesa un reporte confirmatorio.

        La prioridad y la clave son calculadas previamente por
        ReporteService.

        Este método solamente las actualiza en el Sismo y persiste
        el resultado.

        La clave NO se vuelve a calcular aquí.
        """

        station = SismoValidationService.validate_station_id(
            station_id
        )

        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío."
            )

        sismo = self.repository.get_by_id(
            SismoValidationService.validate_id(
                sismo_id
            )
        )

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        # --------------------------------------------------------------
        # Actualizar prioridad y clave
        # --------------------------------------------------------------

        if prioridad is not None:
            sismo.prioridad = (
                SismoValidationService.validate_priority(
                    prioridad
                )
            )

        if clave is not None:
            sismo.clave = (
                SismoValidationService.validate_key(
                    clave
                )
            )

        # --------------------------------------------------------------
        # Agregar estación
        # --------------------------------------------------------------

        sismo.reporting_stations.add(
            station
        )

        # --------------------------------------------------------------
        # Incrementar revisión
        # --------------------------------------------------------------

        sismo.revision += 1

        return self.repository.save(
            sismo
        )

    # ------------------------------------------------------------------
    # CORRECCIÓN
    # ------------------------------------------------------------------

    def apply_correction(
        self,
        sismo_id: int,
        station_id: str,
        magnitude: Optional[float] = None,
        depth: Optional[float] = None,
        epicenter_x: Optional[float] = None,
        epicenter_y: Optional[float] = None,
        prioridad: Optional[int] = None,
        clave: Optional[tuple[int, float, int]] = None,
    ) -> Sismo:
        """
        Procesa una corrección sobre un sismo.

        La prioridad y la clave son calculadas previamente por
        ReporteService.

        Si existe una corrección real:
            - actualiza los datos físicos;
            - actualiza prioridad;
            - actualiza clave;
            - agrega la estación;
            - incrementa la revisión;
            - establece PENDIENTE;
            - guarda el sismo.

        La clave NO se vuelve a calcular aquí.
        """

        station = SismoValidationService.validate_station_id(
            station_id
        )

        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío "
                "al aplicar corrección."
            )

        sismo = self.repository.get_by_id(
            SismoValidationService.validate_id(
                sismo_id
            )
        )

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        # --------------------------------------------------------------
        # Validar nuevos valores
        # --------------------------------------------------------------

        new_mag = (
            SismoValidationService.validate_magnitude(
                magnitude
            )
            if magnitude is not None
            else sismo.magnitude
        )

        new_depth = (
            SismoValidationService.validate_depth(
                depth
            )
            if depth is not None
            else sismo.depth
        )

        new_x = (
            SismoValidationService.validate_epicenter_coord(
                epicenter_x,
                "epicenter_x"
            )
            if epicenter_x is not None
            else sismo.epicenter_x
        )

        new_y = (
            SismoValidationService.validate_epicenter_coord(
                epicenter_y,
                "epicenter_y"
            )
            if epicenter_y is not None
            else sismo.epicenter_y
        )

        # --------------------------------------------------------------
        # Determinar si realmente hubo un cambio
        # --------------------------------------------------------------

        has_changed = SismoComparison.tiene_cambios(
            sismo=sismo,
            magnitude=new_mag,
            depth=new_depth,
            epicenter_x=new_x,
            epicenter_y=new_y
        )

        # --------------------------------------------------------------
        # CORRECCIÓN REAL
        # --------------------------------------------------------------

        if has_changed:

            sismo.magnitude = new_mag
            sismo.depth = new_depth
            sismo.epicenter_x = new_x
            sismo.epicenter_y = new_y

            # ----------------------------------------------------------
            # Actualizar prioridad y clave
            #
            # La clave ya fue calculada por ReporteService.
            # ----------------------------------------------------------

            if prioridad is not None:
                sismo.prioridad = (
                    SismoValidationService.validate_priority(
                        prioridad
                    )
                )

            if clave is not None:
                sismo.clave = (
                    SismoValidationService.validate_key(
                        clave
                    )
                )

            # ----------------------------------------------------------
            # Registrar estación
            # ----------------------------------------------------------

            sismo.reporting_stations.add(
                station
            )

            # ----------------------------------------------------------
            # Nueva revisión
            # ----------------------------------------------------------

            sismo.revision += 1

            # ----------------------------------------------------------
            # Una corrección requiere nueva revisión
            # ----------------------------------------------------------

            sismo.status = StatusSismo.PENDIENTE

            return self.repository.save(
                sismo
            )

        # --------------------------------------------------------------
        # SI NO CAMBIÓ NINGÚN DATO
        #
        # Se considera una confirmación.
        # --------------------------------------------------------------

        return self.add_consensus_report(
            sismo_id,
            station_id,
            prioridad,
            clave
        )

    # ------------------------------------------------------------------
    # AUDITORÍA Y VALIDACIÓN
    # ------------------------------------------------------------------

    def audit_and_validate(
        self,
        sismo_id: int
    ) -> Sismo:

        sismo = self.repository.get_by_id(
            SismoValidationService.validate_id(
                sismo_id
            )
        )

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        sismo.status = StatusSismo.REVISADO

        return self.repository.save(
            sismo
        )

    # ------------------------------------------------------------------
    # ELIMINAR
    # ------------------------------------------------------------------

    def delete(
        self,
        sismo_id: Any
    ) -> bool:
        """
        Valida el ID del sismo, confirma su existencia y solicita
        su eliminación al repositorio.
        """

        val_id = SismoValidationService.validate_id(
            sismo_id
        )

        sismo = self.repository.get_by_id(
            val_id
        )

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {val_id}."
            )

        return self.repository.delete(
            val_id
        )

    # Alias alternativo
    delete_event = delete

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        sismo_id: int
    ) -> Sismo:

        sismo = self.repository.get_by_id(
            SismoValidationService.validate_id(
                sismo_id
            )
        )

        if not sismo:
            raise SismoNotFoundError(
                f"No se encontró el evento sísmico con ID {sismo_id}."
            )

        return sismo

    def get_all(
        self
    ) -> list[Sismo]:

        return self.repository.get_all()


# ------------------------------------------------------------------
    # ACTUALIZAR EVENTO
    # ------------------------------------------------------------------

    def update_event(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
    ) -> Sismo:
        """Actualiza los datos de un evento sísmico existente.

        Realiza la validación de los datos recibidos, determina si existió alguna
        modificación en los parámetros físicos del evento y persiste el nuevo estado.

        Reglas de Negocio:
            - Si cambian los datos físicos (magnitud, profundidad, epicentro_x, epicentro_y):
                * Se actualizan magnitud, profundidad y epicentro.
                * Se incrementa la revisión del evento (`sismo.revision += 1`).
                * Se establece el estado como `StatusSismo.PENDIENTE`.
            - Si solo cambia el timestamp:
                * Se actualiza el timestamp sin modificar el número de revisión ni el estado.
            - Conserva las estaciones reportantes, la prioridad y la clave actuales.

        Args:
            sismo_id (int): Identificador numérico único del sismo.
            magnitude (float): Magnitud del sismo.
            depth (float): Profundidad en kilómetros.
            epicenter_x (float): Longitud / Coordenada X del epicentro.
            epicenter_y (float): Latitud / Coordenada Y del epicentro.
            timestamp (datetime | str): Fecha y hora del evento sísmico.

        Returns:
            Sismo: La entidad `Sismo` actualizada y persistida en el repositorio.

        Raises:
            SismoNotFoundError: Si no existe un evento sísmico registrado con el ID proporcionado.
            SismoValidationError: Si alguno de los valores recibidos no supera la validación.
        """
        # 1. Validar ID y recuperar la entidad existente
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(f"No existe el evento sísmico con ID {val_id}.")

        # 2. Validar tipos y rangos de los nuevos parámetros
        new_mag = SismoValidationService.validate_magnitude(magnitude)
        new_depth = SismoValidationService.validate_depth(depth)
        new_x = SismoValidationService.validate_epicenter_coord(epicenter_x, "epicenter_x")
        new_y = SismoValidationService.validate_epicenter_coord(epicenter_y, "epicenter_y")
        new_timestamp = SismoValidationService.validate_timestamp(timestamp)

        # 3. Determinar si hubo variaciones en los datos físicos
        has_changed = SismoComparison.tiene_cambios(
            sismo=sismo,
            magnitude=new_mag,
            depth=new_depth,
            epicenter_x=new_x,
            epicenter_y=new_y,
        )

        # 4. Asignar los nuevos valores a la entidad
        sismo.magnitude = new_mag
        sismo.depth = new_depth
        sismo.epicenter_x = new_x
        sismo.epicenter_y = new_y
        sismo.timestamp = new_timestamp

        # 5. Aplicar lógica de revisión si hubo modificaciones físicas
        if has_changed:
            sismo.revision += 1
            sismo.status = StatusSismo.PENDIENTE

        # 6. Persistir cambios en el almacenamiento
        return self.repository.save(sismo)