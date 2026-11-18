"""CuentaMesa — servidor web. Ejecutar:  python app.py  y abrir http://localhost:5000"""
import os
from datetime import timedelta
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from jinja2 import DictLoader

import datos
from modelos import (Cuenta, ErrorNegocio, EstadoCuenta, EstadoDetalleOrden, Orden,
                     PagoEfectivo, PagoTarjeta, RolUsuario)
from plantillas import PLANTILLAS
from terminal import TerminalSimulada

MESERO, CAJERO = RolUsuario.MESERO, RolUsuario.CAJERO

app = Flask(__name__)
app.secret_key = os.environ.get("CLAVE_SECRETA", "cambia-esta-clave")
app.permanent_session_lifetime = timedelta(minutes=15)  # RNF-02: cierre tras 15 min sin actividad
app.jinja_env.loader = DictLoader(PLANTILLAS)
terminal = TerminalSimulada()


# ---------- Utilidades ----------
@app.before_request
def cargar_usuario():
    g.usuario = datos.usuarios.get(session.get("usuario"))


@app.context_processor
def variables_globales():
    return {"usuario": g.get("usuario")}


@app.errorhandler(ErrorNegocio)
def error_negocio(e):
    flash(str(e))
    return redirect(request.referrer or url_for("inicio"))


def requiere(rol=None):
    """Exige sesión iniciada y, si se indica, un rol."""
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if not g.usuario:
                return redirect(url_for("login"))
            if rol and not g.usuario.validarRol(rol):
                abort(403)
            return funcion(*args, **kwargs)
        return envoltura
    return decorador


def obtener_cuenta(folio):
    cuenta = datos.cuentas.get(folio) or abort(404)
    if g.usuario.validarRol(MESERO) and cuenta.mesero is not g.usuario:
        abort(403)  # el mesero solo opera sus cuentas
    return cuenta


def buscar_detalle(cuenta, id):
    for orden in cuenta.ordenes:
        for detalle in orden.detalles:
            if detalle.idDetalle == id:
                return orden, detalle
    abort(404)


def volver(cuenta):
    return redirect(url_for("ver_cuenta", folio=cuenta.folio))


# ---------- Sesión (RF-01) ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = datos.usuarios.get(request.form.get("usuario", ""))
        if u and u.autenticar(request.form.get("contrasena")):
            session.clear()
            session.permanent = True
            session["usuario"] = u.nombreUsuario
            return redirect(url_for("inicio"))
        flash("Usuario o contraseña incorrectos.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requiere()
def inicio():
    return redirect(url_for("mesas" if g.usuario.validarRol(MESERO) else "caja"))


# ---------- Menú (RF-02, RF-15) ----------
@app.route("/menu")
@requiere()
def menu():
    return render_template("menu.html", categorias=datos.categorias)


@app.post("/menu/productos", defaults={"id": None})
@app.post("/menu/productos/<int:id>")
@requiere(CAJERO)
def guardar_producto(id):
    f = request.form
    if id is None:
        cat = next((c for c in datos.categorias if c.idCategoria == f.get("categoria", type=int)), None) or abort(404)
        datos.agregar_producto(f.get("nombre"), f.get("precio"), cat)
    else:
        p = datos.productos.get(id) or abort(404)
        p.actualizarDatos(f.get("nombre"), f.get("precio"))
        p.marcarDisponible("disponible" in f)
    flash("Producto guardado.")
    return redirect(url_for("menu"))


# ---------- Mesero (RF-03 a RF-10) ----------
@app.route("/mesas")
@requiere(MESERO)
def mesas():
    filas = [(m, datos.cuenta_activa(m)) for m in datos.mesas.values()]
    return render_template("mesas.html", filas=filas)


@app.post("/cuentas")
@requiere(MESERO)
def abrir_cuenta():
    mesa = datos.mesas.get(request.form.get("mesa", type=int)) or abort(404)
    cuenta = Cuenta(len(datos.cuentas) + 1, mesa, g.usuario, request.form.get("comensales"))
    cuenta.agregarOrden(Orden(1), g.usuario)  # primera orden lista para capturar
    datos.cuentas[cuenta.folio] = cuenta
    return volver(cuenta)


@app.route("/cuentas/<int:folio>")
@requiere()
def ver_cuenta(folio):
    return render_template("cuenta.html", cuenta=obtener_cuenta(folio),
                           categorias=datos.categorias, estados=list(EstadoDetalleOrden))


@app.post("/cuentas/<int:folio>/ordenes")
@requiere(MESERO)
def nueva_orden(folio):
    cuenta = obtener_cuenta(folio)
    cuenta.agregarOrden(Orden(len(cuenta.ordenes) + 1), g.usuario)
    return volver(cuenta)


@app.post("/cuentas/<int:folio>/ordenes/<int:id>")
@requiere(MESERO)
def agregar_producto(folio, id):
    cuenta = obtener_cuenta(folio)
    cuenta.validarMesero(g.usuario)
    orden = next((o for o in cuenta.ordenes if o.idOrden == id), None) or abort(404)
    producto = datos.productos.get(request.form.get("producto", type=int)) or abort(404)
    orden.agregarDetalle(producto, request.form.get("cantidad"), request.form.get("nota"))
    return volver(cuenta)


@app.post("/cuentas/<int:folio>/detalles/<int:id>/eliminar")
@requiere(MESERO)
def eliminar_detalle(folio, id):
    cuenta = obtener_cuenta(folio)
    cuenta.validarMesero(g.usuario)
    orden, detalle = buscar_detalle(cuenta, id)
    orden.eliminarDetalle(detalle)
    return volver(cuenta)


@app.post("/cuentas/<int:folio>/detalles/<int:id>/estado")
@requiere(MESERO)
def estado_detalle(folio, id):
    cuenta = obtener_cuenta(folio)
    cuenta.validarMesero(g.usuario, (EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR))
    _, detalle = buscar_detalle(cuenta, id)
    detalle.actualizarEstado(request.form.get("estado", ""))
    return volver(cuenta)


@app.post("/cuentas/<int:folio>/solicitar")
@requiere(MESERO)
def solicitar_cobro(folio):
    cuenta = obtener_cuenta(folio)
    cuenta.solicitarCuenta(g.usuario)
    flash("Cuenta enviada a caja.")
    return volver(cuenta)


# ---------- Cajero (RF-11 a RF-14) ----------
@app.route("/caja")
@requiere(CAJERO)
def caja():
    orden_estado = list(EstadoCuenta).index
    cuentas = sorted(datos.cuentas.values(), key=lambda c: (orden_estado(c.estado), -c.folio))
    return render_template("caja.html", cuentas=cuentas)


@app.post("/cuentas/<int:folio>/propina")
@requiere(CAJERO)
def propina(folio):
    cuenta = obtener_cuenta(folio)
    cuenta.aplicarPropina(request.form.get("valor"), request.form.get("tipo") == "porcentaje", g.usuario)
    return volver(cuenta)


@app.post("/cuentas/<int:folio>/pagar")
@requiere(CAJERO)
def pagar(folio):
    cuenta = obtener_cuenta(folio)
    if request.form.get("metodo") == "TARJETA":
        if not PagoTarjeta(g.usuario, terminal).procesarCobro(cuenta):
            flash("Tarjeta rechazada o sin respuesta en 30 s. La cuenta sigue por cobrar: "
                  "reintente o cobre en efectivo.")
            return volver(cuenta)
    else:
        pago = PagoEfectivo(g.usuario, request.form.get("recibido"))
        pago.procesarCobro(cuenta)
        flash(f"Pago registrado. Cambio: ${pago.cambio}")
    return redirect(url_for("ticket", folio=folio))


@app.post("/cuentas/<int:folio>/cancelar")
@requiere(CAJERO)
def cancelar(folio):
    cuenta = obtener_cuenta(folio)
    cuenta.cancelar(request.form.get("motivo"), g.usuario)
    flash(f"Cuenta {folio} cancelada; la mesa {cuenta.mesa.numero} quedó libre.")
    return redirect(url_for("caja"))


@app.route("/cuentas/<int:folio>/ticket")
@requiere(CAJERO)
def ticket(folio):
    cuenta = obtener_cuenta(folio)
    if not cuenta.pago:
        raise ErrorNegocio("La cuenta no tiene un pago registrado (RN-14).")
    return render_template("ticket.html", texto=cuenta.pago.generarTicket(cuenta), folio=folio)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # 0.0.0.0 para que las tabletas de la red local entren