from datetime import datetime

from src.Models.Referencia import Referencia
from src.Models.ReferenciaSismo import ReferenciaSismo
from src.Models.Sismo import EstadoPersistencia
from src.business.algortimos.sismos.referencia_sismo import (
    calcular_distancia,
    es_referencia_candidata,
)


class ReferenciaSismoService:
    """Calculates and persists deterministic event associations."""

    def __init__(
        self,
        sismo_repository,
        referencia_repository,
        historico_repository=None,
        eliminados_service=None,
    ):
        self.sismo_repository = sismo_repository
        self.referencia_repository = referencia_repository
        self.historico_repository = historico_repository
        self.eliminados_service = eliminados_service

    def _eventos(self):
        eventos = list(self.sismo_repository.get_all())
        if self.historico_repository is not None:
            eventos.extend(self.historico_repository.get_all())
        retirados = (
            self.eliminados_service.todos()
            if self.eliminados_service is not None
            else set()
        )
        return [
            evento for evento in eventos
            if evento.estado_persistencia != EstadoPersistencia.RETIRADO
            and evento.id not in retirados
        ]

    def _es_candidata(self, candidato, evento):
        return es_referencia_candidata(
            candidato,
            evento,
            ventana_horas=self.referencia_repository.ventana_horas,
            radio_km=self.referencia_repository.radio_km,
        )

    def obtener_candidatos(self, sismo):
        candidatos = []
        for evento in self._eventos():
            if evento.id == sismo.id or not self._es_candidata(evento, sismo):
                continue
            distancia = calcular_distancia(
                evento.epicenter_x,
                evento.epicenter_y,
                sismo.epicenter_x,
                sismo.epicenter_y,
            )
            candidatos.append(Referencia(
                id=evento.id,
                distancia=distancia,
                magnitud=evento.magnitude,
            ))
        return sorted(candidatos, key=lambda item: (item.distancia, -item.magnitud, item.id))

    def _evento_por_id(self, sismo_id):
        for evento in self._eventos():
            if evento.id == sismo_id:
                return evento
        return None

    def obtener_referencia(self, sismo_id):
        return self.referencia_repository.obtener_por_sismo(sismo_id)

    def guardar_referencia(self, sismo_id, referencia_id):
        sismo = self._evento_por_id(sismo_id)
        referencia = self._evento_por_id(referencia_id)
        if sismo is None:
            raise ValueError(f"No existe el sismo {sismo_id}")
        if referencia is None:
            raise ValueError(f"No existe el sismo {referencia_id}")
        if sismo_id == referencia_id:
            raise ValueError("Un sismo no puede ser referencia de sí mismo.")
        if not self._es_candidata(referencia, sismo):
            raise ValueError("El sismo seleccionado no cumple los criterios para ser referencia.")
        relacion = ReferenciaSismo(
            sismo_id=sismo_id,
            referencia_id=referencia_id,
            distancia=calcular_distancia(
                referencia.epicenter_x, referencia.epicenter_y,
                sismo.epicenter_x, sismo.epicenter_y,
            ),
            fecha_creacion=datetime.now(),
        )
        return self.referencia_repository.guardar(relacion)

    def recalcular_todas(self) -> None:
        eventos = self._eventos()
        ids_validos = {evento.id for evento in eventos}
        for evento in eventos:
            candidatos = self.obtener_candidatos(evento)
            if candidatos:
                actual = self.obtener_referencia(evento.id)
                # Same reference and distance as before -> keep it as it is.
                # Saving it again changed fecha_creacion on every request, so
                # even a rejected action (an error 400) looked like a change
                # and was recorded in the undo stack.
                if (actual is not None
                        and actual.referencia_id == candidatos[0].id
                        and abs(actual.distancia - candidatos[0].distancia) < 1e-9):
                    continue
                self.guardar_referencia(evento.id, candidatos[0].id)
            else:
                self.referencia_repository.eliminar_por_sismo(evento.id)
        for relacion in self.referencia_repository.todos():
            if relacion.sismo_id not in ids_validos or relacion.referencia_id not in ids_validos:
                self.referencia_repository.eliminar_por_sismo(relacion.sismo_id)

    def configurar(self, ventana_horas, radio_km) -> dict:
        try:
            ventana_horas = float(ventana_horas)
            radio_km = float(radio_km)
        except (TypeError, ValueError):
            raise ValueError("W y R deben ser números positivos.")
        if ventana_horas <= 0 or radio_km <= 0:
            raise ValueError("W y R deben ser números positivos.")
        self.referencia_repository.configurar(ventana_horas, radio_km)
        self.recalcular_todas()
        return self.configuracion()

    def configuracion(self) -> dict:
        return {
            "ventana_horas": self.referencia_repository.ventana_horas,
            "radio_km": self.referencia_repository.radio_km,
        }

    def estado(self) -> dict:
        return self.referencia_repository.exportar()

    def _estado_evento(self, evento) -> str:
        return evento.estado_persistencia.value

    def eventos_que_usan_como_referencia(self, referencia_id: int) -> list[dict]:
        """Returns receivers that currently point to the given event."""
        resultado = []
        for relacion in self.referencia_repository.todos():
            if relacion.referencia_id != referencia_id:
                continue
            evento = self._evento_por_id(relacion.sismo_id)
            if evento is not None:
                resultado.append({
                    "id": evento.id,
                    "estado": self._estado_evento(evento),
                    "referencia": relacion.to_dict(),
                })
        return sorted(resultado, key=lambda item: item["id"])

    def consulta_asociaciones(self, sismo_id: int) -> dict:
        """Returns candidates, selected reference and reverse associations."""
        evento = self._evento_por_id(sismo_id)
        if evento is None:
            raise ValueError(f"No existe el sismo {sismo_id}")

        candidatos = []
        for candidato in self.obtener_candidatos(evento):
            candidato_evento = self._evento_por_id(candidato.id)
            datos = candidato.to_dict()
            datos["estado"] = self._estado_evento(candidato_evento)
            candidatos.append(datos)

        relacion = self.obtener_referencia(sismo_id)
        referencia = None
        if relacion is not None:
            referencia_evento = self._evento_por_id(relacion.referencia_id)
            if referencia_evento is not None:
                referencia = relacion.to_dict()
                referencia["estado"] = self._estado_evento(referencia_evento)

        return {
            "sismo_id": sismo_id,
            "estado": self._estado_evento(evento),
            "candidatos": candidatos,
            "referencia": referencia,
            "eventos_que_lo usan_como_referencia": (
                self.eventos_que_usan_como_referencia(sismo_id)
            ),
            "configuracion": self.configuracion(),
        }
