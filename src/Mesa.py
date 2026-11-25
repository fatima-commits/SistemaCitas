"""Clase Mesa (Tarjeta CRC 2)."""
from Enums import EstadoMesa
from Errores import ReglaNegocioError

# SUP-01: límites de las mesas definidos como constantes.
NUMERO_MESA_MINIMO = 1
NUMERO_MESA_MAXIMO = 40
CAPACIDAD_MESA_MINIMA = 1
CAPACIDAD_MESA_MAXIMA = 12


class Mesa:
    def __init__(self, numero, capacidad):
        # REFACTOR con el codigo de antes: números mágicos 40 y 12 (SUP-01).
        # con la REFACTORIZACION R-05: Estos números se movieron a constantes definidas.
        if not NUMERO_MESA_MINIMO <= numero <= NUMERO_MESA_MAXIMO:
            raise ReglaNegocioError(
                f"El número de mesa debe estar entre "
                f"{NUMERO_MESA_MINIMO} y {NUMERO_MESA_MAXIMO}."
        )
        if not CAPACIDAD_MESA_MINIMA <= capacidad <= CAPACIDAD_MESA_MAXIMA:
            raise ReglaNegocioError(
                f"La capacidad debe estar entre "
                f"{CAPACIDAD_MESA_MINIMA} y {CAPACIDAD_MESA_MAXIMA}."
        )
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



# ---------- Casos de Validaciones internas R-05 (SUP-01) ----------
# REFACTOR R-05: Estos números se movieron a constantes definidas.
# CV-MESA-01 (Correcto): mesa dentro de los límites (número 1, capacidad 1).
# CV-MESA-02 (Correcto): mesa dentro de los límites máximos (40, capacidad 12).
# CV-MESA-03 (Error): número menor que 1 o mayor que 40; debe rechazarse.
# CV-MESA-04 (Error): capacidad menor que 1 o mayor que 12; debe rechazarse.
# CV-MESA-05 (Correcto): una mesa libre puede ocuparse y luego liberarse.
# CV-MESA-06 (Error): ocupar una mesa ya ocupada debe rechazarse.

def verificar_casos():
    """Ejecuta casos de verificación básicos de Mesa sin dependencias de pytest."""
    casos = []

    # CV-MESA-01 y CV-MESA-02: límites válidos.
    casos.append((
        "CV-MESA-01/02 - límites válidos",
        lambda: (Mesa(NUMERO_MESA_MINIMO, CAPACIDAD_MESA_MINIMA),
                Mesa(NUMERO_MESA_MAXIMO, CAPACIDAD_MESA_MAXIMA)),
    ))

    # CV-MESA-03: límites inválidos para el número.
    def numero_invalido():
        for numero in (NUMERO_MESA_MINIMO - 1, NUMERO_MESA_MAXIMO + 1):
            try:
                Mesa(numero, 4)
            except ReglaNegocioError:
                continue
            raise AssertionError(f"Se aceptó el número inválido {numero}.")
    casos.append(("CV-MESA-03 - número fuera de límites", numero_invalido))

    # CV-MESA-04: límites inválidos para la capacidad.
    def capacidad_invalida():
        for capacidad in (CAPACIDAD_MESA_MINIMA - 1, CAPACIDAD_MESA_MAXIMA + 1):
            try:
                Mesa(1, capacidad)
            except ReglaNegocioError:
                continue
            raise AssertionError(f"Se aceptó la capacidad inválida {capacidad}.")
    casos.append(("CV-MESA-04 - capacidad fuera de límites", capacidad_invalida))

    # CV-MESA-05: transición libre -> ocupada -> libre.
    def cambio_estado():
        mesa = Mesa(1, 4)
        assert mesa.estado == EstadoMesa.LIBRE
        mesa.ocupar()
        assert mesa.estado == EstadoMesa.OCUPADA
        mesa.liberar()
        assert mesa.estado == EstadoMesa.LIBRE
    casos.append(("CV-MESA-05 - cambio de estado", cambio_estado))

    # CV-MESA-06: no se permite ocupar dos veces.
    def ocupar_dos_veces():
        mesa = Mesa(1, 4)
        mesa.ocupar()
        try:
            mesa.ocupar()
        except ReglaNegocioError:
            return
        raise AssertionError("Se permitió ocupar una mesa que ya estaba ocupada.")
    casos.append(("CV-MESA-06 - mesa ya ocupada", ocupar_dos_veces))

    for nombre, ejecutar in casos:
        ejecutar()
        print(f"{nombre}: CUMPLE")


if __name__ == "__main__":
    verificar_casos()
