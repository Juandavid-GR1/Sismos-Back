from dataclasses import dataclass
from typing import Any

from src.Models.Sismo import Sismo


@dataclass
class AccionSismo:
    """Snapshot of one user-visible structural action."""

    tipo: str
    eventos: list[Sismo]
    ids_retirados_antes: set[int]
    metadatos: dict[str, Any]
