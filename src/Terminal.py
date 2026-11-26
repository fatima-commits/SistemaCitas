"""Interfaz ServicioTerminalPago (inversión de dependencia hacia el sistema externo)
y una terminal simulada para poder probar sin banco."""
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoCargo:
    """Objeto de valor que encapsula la respuesta atómica de la terminal."""
    aprobado: bool
    referencia: str = ""

class ServicioTerminalPago(ABC):
    @abstractmethod
    def enviar_cargo(self, monto):
        """Envia un cargo a la terminal bancaria y devuelve un ResultadoCargo."""

class TerminalSimulada(ServicioTerminalPago):
    """Simula la terminal bancaria: tarda un poco y a veces rechaza."""

    def __init__(self, probabilidad_aprobacion=0.8, demora_maxima_seg=2.0):
        self._probabilidad_aprobacion = probabilidad_aprobacion
        self._demora_maxima_seg = demora_maxima_seg

    def enviar_cargo(self, monto):
        time.sleep(random.uniform(0, self._demora_maxima_seg))
        aprobado = random.random() < self._probabilidad_aprobacion
        referencia = f"REF-{uuid.uuid4().hex[:8].upper()}" if aprobado else ""
        return ResultadoCargo(aprobado=aprobado, referencia=referencia)