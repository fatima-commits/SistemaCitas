from decimal import Decimal
import pytest

from Enums import EstadoCuenta, EstadoMesa
from Errores import ReglaNegocioError
from Pago import PagoEfectivo, PagoTarjeta
from Repositorio import RepositorioMemoria
from Terminal import ResultadoCargo, ServicioTerminalPago
from Ticket import GeneradorTicket

class TerminalPrueba(ServicioTerminalPago):
    def __init__(self, aprobar=True):
        self._aprobar = aprobar
        self._ref = "REF-TEST01" if aprobar else ""

    def enviar_cargo(self, monto):
        return ResultadoCargo(aprobado=self._aprobar, referencia=self._ref)


def test_abrir_cuenta():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    assert cuenta.estado == EstadoCuenta.ABIERTA
    assert repo.buscar_mesa(1).estado == EstadoMesa.OCUPADA


def test_abrir_cuenta_mesa_ocupada():
    repo = RepositorioMemoria()
    mesero1 = repo.buscar_usuario_por_nombre("mesero1")
    mesero2 = repo.buscar_usuario_por_nombre("mesero2")
    repo.abrir_cuenta(1, mesero1, 2)
    with pytest.raises(ReglaNegocioError):
        repo.abrir_cuenta(1, mesero2, 2)


def test_agregar_orden():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    orden = cuenta.agregar_orden(mesero)
    assert orden.numero_en_cuenta == 1
    assert len(cuenta.ordenes) == 1


def test_agregar_orden_mesero_ajeno():
    repo = RepositorioMemoria()
    mesero1 = repo.buscar_usuario_por_nombre("mesero1")
    mesero2 = repo.buscar_usuario_por_nombre("mesero2")
    cuenta = repo.abrir_cuenta(1, mesero1, 2)
    with pytest.raises(ReglaNegocioError):
        cuenta.agregar_orden(mesero2)


def test_agregar_producto():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    tacos = repo.buscar_producto(3)
    horchata = repo.buscar_producto(6)
    d1 = cuenta.agregar_producto(1, tacos, 2, "sin cebolla", mesero)
    d2 = cuenta.agregar_producto(1, horchata, 1, "", mesero)
    assert d1.calcular_importe() == Decimal("240.00")
    assert d1.nota == "sin cebolla"
    assert d2.calcular_importe() == Decimal("40.00")


def test_agregar_producto_no_disponible():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    arrachera = repo.buscar_producto(5)
    with pytest.raises(ReglaNegocioError):
        cuenta.agregar_producto(1, arrachera, 1, "", mesero)


def test_calcular_totales():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(3), 2, "", mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(6), 1, "", mesero)
    assert cuenta.calcular_subtotal() == Decimal("241.38")
    assert cuenta.calcular_iva() == Decimal("38.62")
    assert cuenta.calcular_consumo() == Decimal("280.00")


def test_cuenta_sin_productos():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    assert cuenta.calcular_subtotal() == Decimal("0.00")
    assert cuenta.calcular_iva() == Decimal("0.00")
    assert cuenta.calcular_consumo() == Decimal("0.00")
    with pytest.raises(ReglaNegocioError):
        cuenta.solicitar_cuenta(mesero)


def test_aplicar_propina():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(3), 2, "", mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(6), 1, "", mesero)
    cuenta.solicitar_cuenta(mesero)
    cuenta.aplicar_propina("10", True, cajero)
    assert cuenta.propina == Decimal("28.00")
    assert cuenta.calcular_total_a_pagar() == Decimal("308.00")


def test_aplicar_propina_negativa():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(1), 1, "", mesero)
    cuenta.solicitar_cuenta(mesero)
    with pytest.raises(ReglaNegocioError):
        cuenta.aplicar_propina("-15", False, cajero)


def test_cobrar_cuenta():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")

    c1 = repo.abrir_cuenta(1, mesero, 2)
    c1.agregar_orden(mesero)
    c1.agregar_producto(1, repo.buscar_producto(1), 1, "", mesero)
    c1.solicitar_cuenta(mesero)
    pago_ef = PagoEfectivo(cajero, "100.00")
    assert pago_ef.procesar_cobro(c1) is True
    assert pago_ef.cambio == Decimal("5.00")
    assert c1.estado == EstadoCuenta.PAGADA
    assert c1.mesa.estado == EstadoMesa.LIBRE

    c2 = repo.abrir_cuenta(2, mesero, 2)
    c2.agregar_orden(mesero)
    c2.agregar_producto(1, repo.buscar_producto(1), 1, "", mesero)
    c2.solicitar_cuenta(mesero)
    pago_tj = PagoTarjeta(cajero, TerminalPrueba(aprobar=True))
    assert pago_tj.procesar_cobro(c2) is True
    assert c2.estado == EstadoCuenta.PAGADA


def test_cobrar_cuenta_error():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(1), 1, "", mesero)
    cuenta.solicitar_cuenta(mesero)
    assert PagoEfectivo(cajero, "50.00").procesar_cobro(cuenta) is False
    assert PagoTarjeta(cajero, TerminalPrueba(aprobar=False)).procesar_cobro(cuenta) is False
    assert cuenta.estado == EstadoCuenta.POR_COBRAR
    assert cuenta.pago is None


def test_generar_ticket():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    cuenta.agregar_orden(mesero)
    cuenta.agregar_producto(1, repo.buscar_producto(1), 1, "", mesero)
    cuenta.solicitar_cuenta(mesero)
    pago = PagoEfectivo(cajero, "100.00")
    pago.procesar_cobro(cuenta)
    ticket = GeneradorTicket().generar(cuenta.generar_resumen(), [pago])
    assert "Folio cuenta: 1" in ticket
    assert "Guacamole" in ticket


def test_generar_ticket_sin_pago():
    repo = RepositorioMemoria()
    mesero = repo.buscar_usuario_por_nombre("mesero1")
    cajero = repo.buscar_usuario_por_nombre("cajero1")
    cuenta = repo.abrir_cuenta(1, mesero, 2)
    pago = PagoEfectivo(cajero, "100.00")
    with pytest.raises(ReglaNegocioError):
        GeneradorTicket().generar(cuenta.generar_resumen(), [pago])


def test_crear_producto():
    repo = RepositorioMemoria()
    producto = repo.crear_producto("Tarta de elote", "75.00", 4, True)
    assert producto.nombre == "Tarta de elote"
    assert producto.precio == Decimal("75.00")
    assert producto.disponible is True


def test_crear_producto_invalido():
    repo = RepositorioMemoria()
    with pytest.raises(ReglaNegocioError):
        repo.crear_producto("", "-10.00", 4, True)