"""Clase abstracta Pago y sus subclases (Tarjetas CRC 5, 6 y 7)."""
import itertools
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from Enums import EstadoCuenta, MetodoPago, RolUsuario
from Errores import ReglaNegocioError


# REFACTOR: función DUPLICADA de cuenta.py. Unificar en un solo módulo.
def redondear(valor):
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    def _lineas_metodo(self):
        """Hook: cada subclase agrega sus propias líneas al ticket."""
        return []

    def generar_ticket(self, cuenta):
        """RF-14, RN-14: solo si la cuenta tiene este pago registrado."""
        if cuenta.pago is not self:
            raise ReglaNegocioError("La cuenta no tiene un pago registrado (RN-14).")
        # REFACTOR: el formato del ticket está armado a mano con strings.
        # Separarlo en una clase GeneradorTicket (o una plantilla) para que Pago
        # no tenga dos responsabilidades (cobrar y dar formato).
        lineas = [
            "CUENTAMESA",
            f"Folio cuenta: {cuenta.folio}   Mesa: {cuenta.mesa.numero}",
            f"Mesero: {cuenta.mesero.nombre}   Comensales: {cuenta.numero_comensales}",
            f"Fecha: {self._fecha_hora:%d/%m/%Y %H:%M}",
            "-" * 40,
        ]
        for orden in cuenta.ordenes:
            for d in orden.detalles:
                lineas.append(f"{d.cantidad:>3} x {d.producto.nombre[:22]:<22} {d.calcular_importe():>10.2f}")
        lineas += [
            "-" * 40,
            f"{'Subtotal':<28}{cuenta.calcular_subtotal():>12.2f}",
            f"{'IVA 16%':<28}{cuenta.calcular_iva():>12.2f}",
            f"{'Consumo':<28}{cuenta.calcular_consumo():>12.2f}",
            f"{'Propina':<28}{cuenta.propina:>12.2f}",
            f"{'TOTAL':<28}{self._monto:>12.2f}",
            f"Pago: {self._metodo.value}",
        ]
        lineas += self._lineas_metodo()
        lineas.append("¡Gracias por su visita!")
        return "\n".join(lineas)


class PagoEfectivo(Pago):
    def __init__(self, cajero, monto_recibido):
        super().__init__(cajero, MetodoPago.EFECTIVO)
        try:
            self._monto_recibido = redondear(Decimal(str(monto_recibido)))
        except InvalidOperation:
            raise ReglaNegocioError("Monto recibido no válido.")
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

    def _lineas_metodo(self):
        return [
            f"{'Recibido':<28}{self._monto_recibido:>12.2f}",
            f"{'Cambio':<28}{self._cambio:>12.2f}",
            f"Folio caja: {self._folio_caja}",
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

        # REFACTOR: se crea un pool de hilos en cada cobro. Se podría compartir
        # uno para toda la app, o mover el manejo del tiempo límite a un
        # decorador/clase que envuelva a la terminal.
        inicio = time.monotonic()
        pool = ThreadPoolExecutor(max_workers=1)
        futuro = pool.submit(self._terminal.enviar_cargo, total)
        try:
            aprobado = futuro.result(timeout=self.LIMITE_SEGUNDOS)
        except TiempoAgotado:
            aprobado = False
        except Exception:  # la terminal falló (red, etc.): se trata como rechazo
            aprobado = False
        finally:
            pool.shutdown(wait=False)
        self._tiempo_respuesta_seg = round(time.monotonic() - inicio)

        self._aprobado = aprobado and self.verificar_tiempo_limite()
        if not self._aprobado:
            return False  # rechazada o sin respuesta: la cuenta sigue por cobrar
        self._referencia_terminal = self._terminal.obtener_referencia()
        self._registrar(cuenta, total)
        return True

    def _lineas_metodo(self):
        return [f"Referencia terminal: {self._referencia_terminal}"]