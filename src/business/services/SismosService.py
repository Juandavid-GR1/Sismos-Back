from datetime import datetime
from typing import Any, Optional, Protocol

from src.business.algortimos.sismos.SismoComparison import SismoComparison
from src.business.algortimos.sismos.SismoValidationService import (
    SismoValidationError,
    SismoValidationService,
)
from src.Models.Sismo import Sismo, StatusSismo


class SismoNotFoundError(KeyError):
    """Excepción lanzada cuando no se encuentra un evento sísmico en el sistema."""

    pass


class ISismoRepository(Protocol):
    """Interfaz (Protocolo) para abstraer la capa de persistencia de sismos."""

    def get_by_id(self, sismo_id: int) -> Optional[Sismo]:
        """Obtiene un sismo por su ID único."""
        ...

    def get_all(self) -> list[Sismo]:
        """Recupera la lista completa de sismos."""
        ...

    def save(self, sismo: Sismo) -> Sismo:
        """Guarda o actualiza un sismo en el almacén de datos."""
        ...

    def delete(self, sismo_id: int) -> bool:
        """Elimina un sismo según su ID."""
        ...

    def generate_next_id(self) -> int:
        """Genera el siguiente identificador numérico disponible."""
        ...


class SismoService:
    """Capa de servicio para la gestión de entidades Sismo.

    Implementa la lógica de negocio relativa a la creación, actualización,
    consenso entre estaciones, control de revisiones, priorización y auditoría.
    """

    def __init__(self, repository: ISismoRepository):
        """Inicializa el servicio con su repositorio de persistencia.

        Args:
            repository (ISismoRepository): Instancia del repositorio de sismos.
        """
        self.repository = repository

    # ------------------------------------------------------------------
    # CREACIÓN Y REGISTRO DE EVENTOS
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
        """Crea y persiste un nuevo evento sísmico en el sistema.

        El evento se inicializa en revisión 1, estado PENDIENTE y sin prioridad
        ni clave asignadas hasta que sea procesado por los servicios de reporte.

        Args:
            magnitude (float): Magnitud del sismo.
            depth (float): Profundidad en km.
            epicenter_x (float): Longitud geográfica del epicentro.
            epicenter_y (float): Latitud geográfica del epicentro.
            timestamp (datetime | str): Fecha y hora del evento.
            initial_station_id (Optional[str]): Identificador de la estación emisora.

        Returns:
            Sismo: La entidad del sismo creada y persistida.
        """
        SismoValidationService.validate_station_id(initial_station_id)

        sismo_id = self.repository.generate_next_id()
        SismoValidationService.validate_id(sismo_id)

        sismo = Sismo(
            id=sismo_id,
            magnitude=SismoValidationService.validate_magnitude(magnitude),
            depth=SismoValidationService.validate_depth(depth),
            epicenter_x=SismoValidationService.validate_epicenter_coord(
                epicenter_x, "epicenter_x"
            ),
            epicenter_y=SismoValidationService.validate_epicenter_coord(
                epicenter_y, "epicenter_y"
            ),
            timestamp=SismoValidationService.validate_timestamp(timestamp),
            revision=1,
            reporting_stations=set(),
            prioridad=None,
            clave=None,
            status=StatusSismo.PENDIENTE,
        )

        return self.repository.save(sismo)

    # ------------------------------------------------------------------
    # PROCESAMIENTO DE CONSENSO Y CORRECCIÓN
    # ------------------------------------------------------------------

    def add_consensus_report(
        self,
        sismo_id: int,
        station_id: str,
        prioridad: Optional[int] = None,
        clave: Optional[tuple[int, float, int]] = None,
    ) -> Sismo:
        """Procesa un reporte de confirmación proveniente de una estación.

        Añade la estación a la lista de reportantes sin incrementar la revisión,
        conservando los datos físicos actuales del sismo.

        Args:
            sismo_id (int): ID del sismo a confirmar.
            station_id (str): Identificador de la estación reportante.
            prioridad (Optional[int]): Nueva prioridad asignada, si aplica.
            clave (Optional[tuple[int, float, int]]): Nueva clave asignada, si aplica.

        Returns:
            Sismo: El sismo actualizado con la estación registrada.

        Raises:
            SismoValidationError: Si el identificador de estación es inválido.
            SismoNotFoundError: Si el sismo no existe.
        """
        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío."
            )

        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)
        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        if prioridad is not None:
            sismo.prioridad = SismoValidationService.validate_priority(prioridad)

        if clave is not None:
            sismo.clave = SismoValidationService.validate_key(clave)

        sismo.reporting_stations.add(station)

        return self.repository.save(sismo)

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
        revision: Optional[int] = None,
    ) -> Sismo:
        """Aplica una nueva revisión y actualiza las propiedades físicas del sismo.

        Args:
            sismo_id (int): ID del sismo a corregir.
            station_id (str): Estación que emite la corrección.
            magnitude (Optional[float]): Nueva magnitud medida.
            depth (Optional[float]): Nueva profundidad en km.
            epicenter_x (Optional[float]): Nueva longitud geográfica.
            epicenter_y (Optional[float]): Nueva latitud geográfica.
            prioridad (Optional[int]): Nueva prioridad calculada.
            clave (Optional[tuple[int, float, int]]): Nueva clave calculada.
            revision (Optional[int]): Número de revisión superior recibido.

        Returns:
            Sismo: El sismo actualizado en su nueva revisión.

        Raises:
            SismoValidationError: Si la revisión o los datos físicos son inválidos.
            SismoNotFoundError: Si el sismo no existe.
        """
        station = SismoValidationService.validate_station_id(station_id)
        if not station:
            raise SismoValidationError(
                "El identificador de la estación no puede estar vacío al aplicar corrección."
            )

        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)
        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        # Validación estricta del número de revisión
        if revision is None:
            raise SismoValidationError(
                "La revisión es obligatoria al aplicar una corrección."
            )
        if not isinstance(revision, int):
            raise SismoValidationError("La revisión debe ser un número entero.")
        if revision <= sismo.revision:
            raise SismoValidationError(
                f"La revisión recibida ({revision}) debe ser mayor "
                f"que la revisión actual del sismo ({sismo.revision})."
            )

        # Validación de parámetros físicos
        new_mag = (
            SismoValidationService.validate_magnitude(magnitude)
            if magnitude is not None
            else sismo.magnitude
        )
        new_depth = (
            SismoValidationService.validate_depth(depth)
            if depth is not None
            else sismo.depth
        )
        new_x = (
            SismoValidationService.validate_epicenter_coord(epicenter_x, "epicenter_x")
            if epicenter_x is not None
            else sismo.epicenter_x
        )
        new_y = (
            SismoValidationService.validate_epicenter_coord(epicenter_y, "epicenter_y")
            if epicenter_y is not None
            else sismo.epicenter_y
        )

        has_changed = SismoComparison.tiene_cambios(
            sismo=sismo,
            magnitude=new_mag,
            depth=new_depth,
            epicenter_x=new_x,
            epicenter_y=new_y,
        )

        # Actualización de atributos
        sismo.magnitude = new_mag
        sismo.depth = new_depth
        sismo.epicenter_x = new_x
        sismo.epicenter_y = new_y

        if prioridad is not None:
            sismo.prioridad = SismoValidationService.validate_priority(prioridad)

        if clave is not None:
            sismo.clave = SismoValidationService.validate_key(clave)

        sismo.reporting_stations.add(station)
        sismo.revision = revision

        if has_changed:
            sismo.status = StatusSismo.PENDIENTE

        return self.repository.save(sismo)

    # ------------------------------------------------------------------
    # AUDITORÍA Y ESTADOS
    # ------------------------------------------------------------------

    def audit_and_validate(self, sismo_id: int) -> Sismo:
        """Marca un evento sísmico como verificado y auditado.

        Args:
            sismo_id (int): Identificador único del sismo.

        Returns:
            Sismo: El evento sísmico con estado REVISADO.

        Raises:
            SismoNotFoundError: Si no existe un sismo con el ID provisto.
        """
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {sismo_id}."
            )

        sismo.status = StatusSismo.REVISADO
        return self.repository.save(sismo)

    # ------------------------------------------------------------------
    # ELIMINACIÓN Y MODIFICACIÓN DIRECTA
    # ------------------------------------------------------------------

    def delete(self, sismo_id: Any) -> bool:
        """Valida e instruye la eliminación de un sismo de la persistencia.

        Args:
            sismo_id (Any): Identificador del sismo.

        Returns:
            bool: True si la eliminación fue exitosa.

        Raises:
            SismoNotFoundError: Si el sismo no existe en el sistema.
        """
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {val_id}."
            )

        return self.repository.delete(val_id)

    # Alias alternativo para retrocompatibilidad
    delete_event = delete

    def update_event(
        self,
        sismo_id: int,
        magnitude: float,
        depth: float,
        epicenter_x: float,
        epicenter_y: float,
        timestamp: datetime | str,
    ) -> Sismo:
        """Actualiza manualmente los datos de un sismo al margen de reportes de estación.

        Si existen cambios en las métricas físicas, incrementa la revisión
        administrativa y restablece el estado del sismo a PENDIENTE.

        Args:
            sismo_id (int): Identificador del sismo.
            magnitude (float): Magnitud corregida.
            depth (float): Profundidad corregida en km.
            epicenter_x (float): Nueva longitud del epicentro.
            epicenter_y (float): Nueva latitud del epicentro.
            timestamp (datetime | str): Fecha y hora actualizadas.

        Returns:
            Sismo: La entidad modificada y guardada.

        Raises:
            SismoNotFoundError: Si no se encuentra el evento sísmico.
        """
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(
                f"No existe el evento sísmico con ID {val_id}."
            )

        new_mag = SismoValidationService.validate_magnitude(magnitude)
        new_depth = SismoValidationService.validate_depth(depth)
        new_x = SismoValidationService.validate_epicenter_coord(
            epicenter_x, "epicenter_x"
        )
        new_y = SismoValidationService.validate_epicenter_coord(
            epicenter_y, "epicenter_y"
        )
        new_timestamp = SismoValidationService.validate_timestamp(timestamp)

        has_changed = SismoComparison.tiene_cambios(
            sismo=sismo,
            magnitude=new_mag,
            depth=new_depth,
            epicenter_x=new_x,
            epicenter_y=new_y,
        )

        sismo.magnitude = new_mag
        sismo.depth = new_depth
        sismo.epicenter_x = new_x
        sismo.epicenter_y = new_y
        sismo.timestamp = new_timestamp

        if has_changed:
            sismo.revision += 1
            sismo.status = StatusSismo.PENDIENTE

        return self.repository.save(sismo)

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def get_by_id(self, sismo_id: int) -> Sismo:
        """Obtiene un sismo validando la existencia de su ID.

        Args:
            sismo_id (int): Identificador a buscar.

        Returns:
            Sismo: La entidad encontrada.

        Raises:
            SismoNotFoundError: Si el ID no corresponde a ningún evento guardado.
        """
        val_id = SismoValidationService.validate_id(sismo_id)
        sismo = self.repository.get_by_id(val_id)

        if not sismo:
            raise SismoNotFoundError(
                f"No se encontró el evento sísmico con ID {sismo_id}."
            )

        return sismo

    def get_all(self) -> list[Sismo]:
        """Recupera el listado completo de eventos sísmicos registrados.

        Returns:
            list[Sismo]: Lista de sismos almacenados.
        """
        return self.repository.get_all()