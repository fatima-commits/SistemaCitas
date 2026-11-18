"""Interfaz ServicioTerminalPago (inversión de dependencia hacia el sistema externo)
y una terminal simulada para poder probar sin banco."""
import random
import time
import uuid
from abc import ABC, abstractmethod


class ServicioTerminalPago(ABC):
    @abstractmethod
    def enviar_cargo(self, monto):
        """Envía el monto a la terminal; devuelve True si fue aprobado (RES-02)."""

    @abstractmethod
    def obtener_referencia(self):
        """Devuelve la referencia de la última operación."""

    # REFACTOR: enviar_cargo + obtener_referencia en dos llamadas separadas
    # guarda estado en la terminal ("la última referencia"). Si dos cajeros
    # cobran a la vez, uno podría leer la referencia del otro. Mejor que
    # enviar_cargo devuelva un objeto ResultadoCargo(aprobado, referencia).


class TerminalSimulada(ServicioTerminalPago):
    """Simula la terminal bancaria: tarda un poco y a veces rechaza."""

    # REFACTOR: usa random directamente, lo que la hace difícil de probar.
    # Inyectar un generador aleatorio o crear TerminalQueSiempreAprueba /
    # TerminalQueNoResponde para las pruebas.
    def __init__(self, probabilidad_aprobacion=0.8, demora_maxima_seg=2.0):
        self._probabilidad_aprobacion = probabilidad_aprobacion
        self._demora_maxima_seg = demora_maxima_seg
        self._ultima_referencia = ""

    def enviar_cargo(self, monto):
        time.sleep(random.uniform(0, self._demora_maxima_seg))
        aprobado = random.random() < self._probabilidad_aprobacion
        self._ultima_referencia = f"REF-{uuid.uuid4().hex[:8].upper()}" if aprobado else ""
        return aprobado

    def obtener_referencia(self):
        return self._ultima_referencia