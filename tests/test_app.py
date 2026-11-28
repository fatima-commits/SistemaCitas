"""Pruebas de las rutas Flask (RF-01 a RF-15).

Cada prueba arma lo que necesita: su propio repositorio, su app y sus usuarios.
"""
from app import crear_app
from Enums import EstadoCuenta
from Repositorio import RepositorioMemoria
from Terminal import ResultadoCargo, ServicioTerminalPago


class TerminalPrueba(ServicioTerminalPago):
    def __init__(self, aprobar=True):
        self.aprobar = aprobar

    def enviar_cargo(self, monto):
        return ResultadoCargo(aprobado=self.aprobar, referencia="REF-TEST" if self.aprobar else "")


def iniciar_sesion(app, usuario):
    cliente = app.test_client()
    cliente.post("/login", data={"nombre_usuario": usuario, "contrasena": "1234"})
    return cliente


def preparar_cuenta_por_cobrar(mesero):
    """Cuenta 1 en la mesa 1 con 2 guacamoles ($190.00), enviada a caja."""
    mesero.post("/mesas/1/abrir", data={"comensales": "2"})
    mesero.post("/cuentas/1/ordenes")
    mesero.post("/cuentas/1/ordenes/1/productos", data={"id_producto": "1", "cantidad": "2"})
    mesero.post("/cuentas/1/solicitar")


# ---------- sesión (RF-01) ----------
def test_login_correcto():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    r = app.test_client().post("/login", data={"nombre_usuario": "mesero1", "contrasena": "1234"},
                               follow_redirects=True)
    assert "Mesa 40" in r.text


def test_login_incorrecto():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    r = app.test_client().post("/login", data={"nombre_usuario": "mesero1", "contrasena": "mal"})
    assert "incorrectos" in r.text


def test_ruta_protegida_sin_sesion():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    r = app.test_client().get("/mesas")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_logout():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    mesero = iniciar_sesion(app, "mesero1")
    mesero.get("/logout")
    assert mesero.get("/mesas").status_code == 302


def test_inicio_cajero_va_a_caja():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    cajero = iniciar_sesion(app, "cajero1")
    assert "/caja" in cajero.get("/").headers["Location"]


# ---------- mesero (RF-02 a RF-10) ----------
def test_flujo_mesero():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    mesero = iniciar_sesion(app, "mesero1")
    mesero.post("/mesas/1/abrir", data={"comensales": "2"})
    mesero.post("/cuentas/1/comensales", data={"comensales": "3"})
    mesero.post("/cuentas/1/ordenes")
    mesero.post("/cuentas/1/ordenes/1/productos",
                data={"id_producto": "1", "cantidad": "2", "nota": "sin cebolla"})
    mesero.post("/cuentas/1/ordenes/1/productos", data={"id_producto": "6", "cantidad": "1"})
    mesero.post("/cuentas/1/productos/1/estado", data={"estado": "entregado"})
    mesero.post("/cuentas/1/productos/2/eliminar")
    pagina = mesero.get("/cuentas/1").text
    assert "sin cebolla" in pagina
    assert "$190.00" in pagina
    cuenta = repo.buscar_cuenta(1)
    assert cuenta.numero_comensales == 3
    assert len(cuenta.ordenes[0].detalles) == 1


def test_comensales_invalidos():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    mesero = iniciar_sesion(app, "mesero1")
    r = mesero.post("/mesas/1/abrir", data={"comensales": "99"}, follow_redirects=True)
    assert "RN-05" in r.text


def test_campo_no_numerico():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    mesero = iniciar_sesion(app, "mesero1")
    r = mesero.post("/mesas/1/abrir", data={"comensales": "dos"}, follow_redirects=True)
    assert "número entero" in r.text


def test_solicitar_cuenta():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    assert repo.buscar_cuenta(1).estado == EstadoCuenta.POR_COBRAR


def test_otro_mesero_no_ve_ni_opera_la_cuenta():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    mesero1 = iniciar_sesion(app, "mesero1")
    mesero2 = iniciar_sesion(app, "mesero2")
    mesero1.post("/mesas/1/abrir", data={"comensales": "2"})
    assert mesero2.get("/cuentas/1").status_code == 403
    r = mesero2.post("/cuentas/1/ordenes", follow_redirects=True)
    assert "RN-06" in r.text
    assert len(repo.buscar_cuenta(1).ordenes) == 0


def test_mesero_no_entra_a_caja_ni_al_menu():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    mesero = iniciar_sesion(app, "mesero1")
    assert mesero.get("/caja").status_code == 403
    assert mesero.get("/menu").status_code == 403


# ---------- cajero (RF-11 a RF-14) ----------
def test_caja_y_detalle_de_cuenta():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    assert "Cuentas activas" in cajero.get("/caja").text
    assert "Total a pagar" in cajero.get("/caja/cuentas/1").text


def test_cajero_no_entra_a_mesas():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    cajero = iniciar_sesion(app, "cajero1")
    assert cajero.get("/mesas").status_code == 403


def test_propina_tipo_invalido():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.post("/caja/cuentas/1/propina", data={"valor": "10", "tipo": "otro"},
                    follow_redirects=True)
    assert "no válido" in r.text


def test_propina_y_pago_en_efectivo():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    cajero.post("/caja/cuentas/1/propina", data={"valor": "10", "tipo": "porcentaje"})
    r = cajero.post("/caja/cuentas/1/pago/efectivo", data={"monto_recibido": "300"},
                    follow_redirects=True)
    assert "Cambio: $91.00" in r.text  # 190 + 19 de propina = 209
    assert repo.buscar_cuenta(1).estado == EstadoCuenta.PAGADA


def test_efectivo_insuficiente():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.post("/caja/cuentas/1/pago/efectivo", data={"monto_recibido": "10"},
                    follow_redirects=True)
    assert "no cubre" in r.text
    assert repo.buscar_cuenta(1).estado == EstadoCuenta.POR_COBRAR


def test_tarjeta_rechazada_y_luego_aprobada():
    terminal = TerminalPrueba(aprobar=False)
    app = crear_app(RepositorioMemoria(), terminal)
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.post("/caja/cuentas/1/pago/tarjeta", follow_redirects=True)
    assert "rechazó" in r.text
    terminal.aprobar = True
    r = cajero.post("/caja/cuentas/1/pago/tarjeta", follow_redirects=True)
    assert "REF-TEST" in r.text  # el ticket muestra la referencia


def test_ticket_sin_pago():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.get("/caja/cuentas/1/ticket", follow_redirects=True)
    assert "RN-14" in r.text


def test_cancelar_cuenta():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    cajero.post("/caja/cuentas/1/cancelar", data={"motivo": "Se fueron"})
    assert repo.buscar_cuenta(1).estado == EstadoCuenta.CANCELADA
    assert repo.buscar_mesa(1).esta_libre()


def test_cancelar_sin_motivo():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    preparar_cuenta_por_cobrar(iniciar_sesion(app, "mesero1"))
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.post("/caja/cuentas/1/cancelar", data={"motivo": ""}, follow_redirects=True)
    assert "motivo" in r.text


# ---------- menú (RF-15) ----------
def test_crear_y_editar_producto():
    repo = RepositorioMemoria()
    app = crear_app(repo, TerminalPrueba())
    cajero = iniciar_sesion(app, "cajero1")
    cajero.post("/menu/productos/5",
                data={"nombre": "Arrachera", "precio": "270", "disponible": "on"})
    cajero.post("/menu/productos/5",
                data={"nombre": "Arrachera", "precio": "270", "disponible": "on"})
    producto = repo.buscar_producto(5)
    assert producto.precio == 270
    assert producto.disponible
    assert "Café" in cajero.get("/menu").text


def test_producto_sin_nombre():
    app = crear_app(RepositorioMemoria(), TerminalPrueba())
    cajero = iniciar_sesion(app, "cajero1")
    r = cajero.post("/menu/productos", data={"nombre": "", "precio": "10", "id_categoria": "1"},
                    follow_redirects=True)
    assert "nombre" in r.text
