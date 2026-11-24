"""Clases DetalleOrden, Orden y Cuenta (Tarjetas CRC 3 y 4)."""
import itertools
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from Proyecto.SistemaCitas.src.enums import EstadoCuenta, EstadoDetalleOrden, RolUsuario
from Proyecto.SistemaCitas.src.errores import ReglaNegocioError

# REFACTOR: número mágico. El 16 % de IVA (RN-09) debería venir de configuración.
TASA_IVA = Decimal("0.16")


# REFACTOR: esta función está DUPLICADA en pago.py. Moverla a un módulo
# dinero.py (o crear una clase Dinero) y usarla en ambos lados.
def redondear(valor):
    """RNF-04: todos los montos a 2 decimales."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# REFACTOR: ids generados con contadores globales. Deberían asignarlos el
# repositorio o la base de datos.
_ids_orden = itertools.count(1)
_ids_detalle = itertools.count(1)


class DetalleOrden:
    """Una línea de la orden: producto + cantidad + nota."""

    def __init__(self, producto, cantidad, nota=""):
        if not producto.disponible:
            raise ReglaNegocioError(f"'{producto.nombre}' no está disponible (RN-02).")
        if not isinstance(cantidad, int) or cantidad < 1:
            raise ReglaNegocioError("La cantidad debe ser un entero mayor o igual que 1 (RN-07).")
        self._id_detalle = next(_ids_detalle)
        self._producto = producto
        self._cantidad = cantidad
        self._precio_unitario = producto.precio  # precio congelado al pedirlo
        self._estado = EstadoDetalleOrden.PENDIENTE
        self._nota = ""
        self.agregar_nota(nota)

    @property
    def id_detalle(self):
        return self._id_detalle

    @property
    def producto(self):
        return self._producto

    @property
    def cantidad(self):
        return self._cantidad

    @property
    def nota(self):
        return self._nota

    @property
    def precio_unitario(self):
        return self._precio_unitario

    @property
    def estado(self):
        return self._estado

    def agregar_nota(self, nota):
        """RF-06, RN-07."""
        self._nota = (nota or "").strip()

    def calcular_importe(self):
        """RN-07, RN-09."""
        return redondear(self._precio_unitario * self._cantidad)

    def actualizar_estado(self, estado):
        """RF-08, RN-08. Acepta el enum o su valor en texto."""
        try:
            self._estado = EstadoDetalleOrden(estado)
        except ValueError:
            raise ReglaNegocioError("Estado no permitido (RN-08).")


class Orden:
    def __init__(self, numero_en_cuenta):
        self._id_orden = next(_ids_orden)
        self._numero_en_cuenta = numero_en_cuenta
        self._fecha_hora = datetime.now()
        self._detalles = []

    @property
    def id_orden(self):
        return self._id_orden

    @property
    def numero_en_cuenta(self):
        return self._numero_en_cuenta

    @property
    def fecha_hora(self):
        return self._fecha_hora

    @property
    def detalles(self):
        return list(self._detalles)

    def agregar_detalle(self, producto, cantidad, nota=""):
        """RF-06, RN-02, RN-07."""
        detalle = DetalleOrden(producto, cantidad, nota)
        self._detalles.append(detalle)
        return detalle

    def eliminar_detalle(self, detalle):
        """RF-07."""
        self._detalles.remove(detalle)

    def buscar_detalle(self, id_detalle):
        for detalle in self._detalles:
            if detalle.id_detalle == id_detalle:
                return detalle
        return None

    def calcular_total(self):
        """RF-09."""
        return sum((d.calcular_importe() for d in self._detalles), Decimal("0.00"))


class Cuenta:
    def __init__(self, folio, mesa, mesero, numero_comensales):
        if not mesero.validar_rol(RolUsuario.MESERO):
            raise ReglaNegocioError("Solo un mesero puede abrir cuentas.")
        self._folio = folio
        self._mesa = mesa
        self._mesero = mesero
        self._fecha_apertura = datetime.now()
        self._estado = EstadoCuenta.ABIERTA
        self._numero_comensales = 0
        self._propina = Decimal("0.00")  # RN-10: cero por omisión
        self._motivo_cancelacion = ""
        self._ordenes = []
        self._pago = None
        self.registrar_comensales(numero_comensales, mesero)
        mesa.ocupar()  # RF-03, RN-03, RN-04 (lanza error si ya está ocupada)

    # ---------- propiedades ----------
    @property
    def folio(self):
        return self._folio

    @property
    def mesa(self):
        return self._mesa

    @property
    def mesero(self):
        return self._mesero

    @property
    def fecha_apertura(self):
        return self._fecha_apertura

    @property
    def estado(self):
        return self._estado

    @property
    def numero_comensales(self):
        return self._numero_comensales

    @property
    def propina(self):
        return self._propina

    @property
    def motivo_cancelacion(self):
        return self._motivo_cancelacion

    @property
    def ordenes(self):
        return list(self._ordenes)

    @property
    def pago(self):
        return self._pago

    # ---------- validaciones internas ----------
    # REFACTOR: _validar_duenio y _validar_estado se llaman al inicio de casi
    # todos los métodos. Se podría usar un decorador o el patrón State
    # (una clase por EstadoCuenta que sepa qué operaciones permite).
    def _validar_duenio(self, mesero):
        if mesero.id_usuario != self._mesero.id_usuario:
            raise ReglaNegocioError("Solo el mesero que abrió la cuenta puede operarla (RN-06).")

    def _validar_estado(self, *estados_permitidos):
        if self._estado not in estados_permitidos:
            raise ReglaNegocioError(f"Operación no permitida: la cuenta está {self._estado.value}.")

    # ---------- operaciones del mesero ----------
    def registrar_comensales(self, numero_comensales, mesero):
        """RF-04, RN-05."""
        self._validar_duenio(mesero)
        self._validar_estado(EstadoCuenta.ABIERTA)
        if not isinstance(numero_comensales, int) or not 1 <= numero_comensales <= self._mesa.capacidad:
            raise ReglaNegocioError(
                f"Los comensales deben estar entre 1 y {self._mesa.capacidad} (RN-05)."
            )
        self._numero_comensales = numero_comensales

    def agregar_orden(self, mesero):
        """RF-05, RN-06. Crea una orden nueva y la devuelve."""
        self._validar_duenio(mesero)
        self._validar_estado(EstadoCuenta.ABIERTA)
        orden = Orden(len(self._ordenes) + 1)
        self._ordenes.append(orden)
        return orden

    def buscar_orden(self, numero_en_cuenta):
        for orden in self._ordenes:
            if orden.numero_en_cuenta == numero_en_cuenta:
                return orden
        raise ReglaNegocioError("La orden no existe.")

    def _buscar_detalle(self, id_detalle):
        for orden in self._ordenes:
            detalle = orden.buscar_detalle(id_detalle)
            if detalle:
                return orden, detalle
        raise ReglaNegocioError("El producto no existe en esta cuenta.")

    def agregar_producto(self, numero_orden, producto, cantidad, nota, mesero):
        """RF-06."""
        self._validar_duenio(mesero)
        self._validar_estado(EstadoCuenta.ABIERTA)
        return self.buscar_orden(numero_orden).agregar_detalle(producto, cantidad, nota)

    def eliminar_producto(self, id_detalle, mesero):
        """RF-07: solo el dueño y solo con la cuenta abierta."""
        self._validar_duenio(mesero)
        self._validar_estado(EstadoCuenta.ABIERTA)
        orden, detalle = self._buscar_detalle(id_detalle)
        orden.eliminar_detalle(detalle)

    def actualizar_estado_producto(self, id_detalle, estado, mesero):
        """RF-08, RN-08: el mesero actualiza el estado del producto."""
        if not mesero.validar_rol(RolUsuario.MESERO):
            raise ReglaNegocioError("Solo el mesero actualiza el estado de los productos (RN-08).")
        self._validar_estado(EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR)
        _, detalle = self._buscar_detalle(id_detalle)
        detalle.actualizar_estado(estado)

    def tiene_productos(self):
        return any(orden.detalles for orden in self._ordenes)

    def solicitar_cuenta(self, mesero):
        """RF-10, RN-06, RN-16."""
        self._validar_duenio(mesero)
        self._validar_estado(EstadoCuenta.ABIERTA)
        if not self.tiene_productos():
            raise ReglaNegocioError("No se puede cobrar una cuenta sin productos (RN-16).")
        self._estado = EstadoCuenta.POR_COBRAR

    # ---------- cálculos (RF-09, RN-09, RNF-04) ----------
    def calcular_consumo(self):
        """Suma de las órdenes; ya incluye IVA porque los precios lo incluyen."""
        return redondear(sum((o.calcular_total() for o in self._ordenes), Decimal("0.00")))

    def calcular_subtotal(self):
        return redondear(self.calcular_consumo() / (1 + TASA_IVA))

    def calcular_iva(self):
        # Se calcula por diferencia para que subtotal + IVA == consumo siempre (RNF-04).
        return self.calcular_consumo() - self.calcular_subtotal()

    def calcular_total_a_pagar(self):
        return redondear(self.calcular_consumo() + self._propina)

    # ---------- operaciones del cajero ----------
    def aplicar_propina(self, valor, es_porcentaje, cajero):
        """RF-11, RN-10."""
        # REFACTOR: el parámetro booleano es_porcentaje es un "flag argument".
        # Cambiar por patrón Strategy: PropinaPorcentaje / PropinaMontoFijo,
        # cada una con su método calcular(consumo).
        if not cajero.validar_rol(RolUsuario.CAJERO):
            raise ReglaNegocioError("Solo el cajero aplica la propina.")
        self._validar_estado(EstadoCuenta.POR_COBRAR)
        try:
            valor = Decimal(str(valor))
        except InvalidOperation:
            raise ReglaNegocioError("Valor de propina no válido.")
        if not valor.is_finite() or valor < 0:
            raise ReglaNegocioError("La propina no puede ser negativa (RN-10).")
        if es_porcentaje:
            self._propina = redondear(self.calcular_consumo() * valor / 100)
        else:
            self._propina = redondear(valor)

    def cancelar(self, motivo, cajero):
        """RF-13, RN-13, RN-04."""
        if not cajero.validar_rol(RolUsuario.CAJERO):
            raise ReglaNegocioError("Solo el cajero puede cancelar cuentas (RN-13).")
        self._validar_estado(EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR)
        motivo = (motivo or "").strip()
        if not motivo:
            raise ReglaNegocioError("La cancelación requiere un motivo (RN-13).")
        self._motivo_cancelacion = motivo
        self._estado = EstadoCuenta.CANCELADA
        self._mesa.liberar()

    def registrar_pago(self, pago):
        """Lo llama Pago cuando el cobro fue exitoso. RN-11, RN-04."""
        self._validar_estado(EstadoCuenta.POR_COBRAR)
        if self._pago is not None:
            raise ReglaNegocioError("La cuenta ya tiene un pago (RN-11).")
        self._pago = pago
        self._estado = EstadoCuenta.PAGADA
        self._mesa.liberar()