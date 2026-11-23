"""Clase Mesa (Tarjeta CRC 2)."""
from Enums import EstadoMesa
from Errores import ReglaNegocioError


class Mesa:
    def __init__(self, numero, capacidad):
        # REFACTOR: números mágicos 40 y 12 (SUP-01). Moverlos a constantes
        # o a un archivo de configuración.
        if not 1 <= numero <= 40:
            raise ReglaNegocioError("El número de mesa debe estar entre 1 y 40.")
        if not 1 <= capacidad <= 12:
            raise ReglaNegocioError("La capacidad debe estar entre 1 y 12.")
        self._numero = numero
        self._capacidad = capacidad
        self._estado = EstadoMesa.LIBRE

    @property
    def numero(self):
        return self._numero

    @property
    def capacidad(self):
        return self._capacidad

    @property
    def estado(self):
        return self._estado

    def esta_libre(self):
        return self._estado == EstadoMesa.LIBRE

    def ocupar(self):
        """RN-03, RN-04: una mesa ocupada no puede abrir otra cuenta."""
        if not self.esta_libre():
            raise ReglaNegocioError(f"La mesa {self._numero} ya está ocupada (RN-03).")
        self._estado = EstadoMesa.OCUPADA

    def liberar(self):
        """RN-04."""
        self._estado = EstadoMesa.LIBRE