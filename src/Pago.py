"""Clase abstracta Pago y sus subclases (Tarjetas CRC 5, 6 y 7)."""
import itertools
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from datetime import datetime
from decimal import Decimal, InvalidOperation

from Dinero import redondear
from Enums import EstadoCuenta, MetodoPago, RolUsuario
from Errores import ReglaNegocioError
from Terminal import ResultadoCargo

# REFACTOR: contador global; debería asignarlo el repositorio/BD.
_ids_pago = itertools.count(1)


class Pago(ABC):
    def __init__(self, cajero, metodo):
        if not cajero.validar_rol(RolUsuario.CAJERO):
            raise ReglaNegocioError("Solo el cajero registra pagos.")
        self._id_pago = None
        self._monto = Decimal("0.00")
        self._fecha_hora = None
        self._metodo = metodo
        self._cajero = cajero

    @property
    def id_pago(self):
        return self._id_pago

    @property
    def monto(self):
        return self._monto

    @property
    def fecha_hora(self):
        return self._fecha_hora

    @property
    def metodo(self):
        return self._metodo

    @abstractmethod
    def procesar_cobro(self, cuenta):
        """Devuelve True si el cobro se registró (RF-12, RN-11, RN-12)."""

    def _validar_cuenta_por_cobrar(self, cuenta):
        if cuenta.estado != EstadoCuenta.POR_COBRAR:
            raise ReglaNegocioError("Solo se cobran cuentas en estado 'por cobrar'.")

    def _registrar(self, cuenta, monto):
        """Guarda los datos del pago y se lo asigna a la cuenta (RN-11)."""
        self._id_pago = next(_ids_pago)
        self._monto = monto
        self._fecha_hora = datetime.now()
        cuenta.registrar_pago(self)

    def datos_ticket(self):
        """Datos propios del método de pago para el ticket, sin formato (H-05)."""
        return []


class PagoEfectivo(Pago):
    def __init__(self, cajero, monto_recibido):
        super().__init__(cajero, MetodoPago.EFECTIVO)
        try:
            monto = Decimal(str(monto_recibido))
        except InvalidOperation:
            raise ReglaNegocioError("Monto recibido no válido.") from None
        if not monto.is_finite() or monto < 0:
            raise ReglaNegocioError("Monto recibido no válido.")
        self._monto_recibido = redondear(monto)
        self._cambio = Decimal("0.00")
        self._folio_caja = ""

    @property
    def cambio(self):
        return self._cambio

    def calcular_cambio(self, monto_a_cobrar):
        return redondear(self._monto_recibido - monto_a_cobrar)

    def procesar_cobro(self, cuenta):
        self._validar_cuenta_por_cobrar(cuenta)
        total = cuenta.calcular_total_a_pagar()
        if self._monto_recibido < total:
            return False  # efectivo insuficiente: la cuenta sigue por cobrar
        self._cambio = self.calcular_cambio(total)
        self._registrar(cuenta, total)
        self._folio_caja = f"CAJA-{self._id_pago:05d}"
        return True

    def datos_ticket(self):
        return [
            ("Recibido", self._monto_recibido),
            ("Cambio", self._cambio),
            ("Folio caja", self._folio_caja),
        ]


class PagoTarjeta(Pago):
    # REFACTOR: el límite de 30 s (RN-12) está fijo aquí; moverlo a configuración.
    LIMITE_SEGUNDOS = 30

    def __init__(self, cajero, terminal):
        super().__init__(cajero, MetodoPago.TARJETA)
        self._terminal = terminal  # ServicioTerminalPago (inyectado)
        self._referencia_terminal = ""
        self._aprobado = False
        self._tiempo_respuesta_seg = 0

    def verificar_tiempo_limite(self):
        """RN-12."""
        return self._tiempo_respuesta_seg <= self.LIMITE_SEGUNDOS

    def procesar_cobro(self, cuenta):
        """Envía el total a la terminal; registra el pago solo si aprueba en ≤ 30 s."""
        self._validar_cuenta_por_cobrar(cuenta)
        total = cuenta.calcular_total_a_pagar()

        inicio = time.monotonic()
        pool = ThreadPoolExecutor(max_workers=1)
        futuro = pool.submit(self._terminal.enviar_cargo, total)
        try:
            resultado = futuro.result(timeout=self.LIMITE_SEGUNDOS)
        except TiempoAgotado:
            resultado = ResultadoCargo(aprobado=False)
        except Exception:  # la terminal falló y se trata como rechazo
            resultado = ResultadoCargo(aprobado=False)
        finally:
            pool.shutdown(wait=False)
        self._tiempo_respuesta_seg = round(time.monotonic() - inicio)

        self._aprobado = resultado.aprobado and self.verificar_tiempo_limite()
        if not self._aprobado:
            return False  # rechazada o sin respuesta
        self._referencia_terminal = resultado.referencia
        self._registrar(cuenta, total)
        return True

    def datos_ticket(self):
        return [("Referencia terminal", self._referencia_terminal)]