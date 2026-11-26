"""CuentaMesa - aplicación web (Flask).

Ejecutar:  pip install flask   y luego   python app.py
Abrir:     http://localhost:5000
"""
import os
from datetime import timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from jinja2 import DictLoader

from Cuenta import PropinaMontoFijo, PropinaPorcentaje
from Enums import EstadoCuenta, EstadoDetalleOrden
from Errores import ReglaNegocioError
from Pago import PagoEfectivo, PagoTarjeta
from Plantillas import PLANTILLAS
from Repositorio import RepositorioMemoria
from Terminal import TerminalSimulada
from Ticket import GeneradorTicket

# H-07: cada tipo del formulario se traduce a su estrategia de propina.
TIPOS_PROPINA = {"porcentaje": PropinaPorcentaje, "fijo": PropinaMontoFijo}


def crear_app(repositorio=None, servicio_terminal=None):
    app = Flask(__name__)

    app.secret_key = os.environ.get("CUENTAMESA_SECRET_KEY", "solo-desarrollo")
    app.permanent_session_lifetime = timedelta(minutes=15)  # RNF-02: 15 min sin actividad
    app.jinja_loader = DictLoader(PLANTILLAS)

    repo = repositorio if repositorio is not None else RepositorioMemoria()
    terminal = servicio_terminal if servicio_terminal is not None else TerminalSimulada()

    # Utilidades
    @app.template_filter("dinero")
    def formato_dinero(valor):
        return f"${valor:,.2f}"


    def usuario_actual():
        id_usuario = session.get("id_usuario")
        return repo.buscar_usuario(id_usuario) if id_usuario else None


    @app.context_processor
    def variables_globales():
        return {"usuario": usuario_actual(), "EstadoCuenta": EstadoCuenta,
                "EstadoDetalleOrden": EstadoDetalleOrden}


    def login_requerido(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if usuario_actual() is None:
                flash("Inicia sesión para continuar.", "error")
                return redirect(url_for("login"))
            return vista(*args, **kwargs)
        return envoltura

    @app.errorhandler(ReglaNegocioError)
    def manejar_regla_negocio(error):
        """Cualquier RN violada se muestra como mensaje y regresa a la página anterior."""
        flash(str(error), "error")

        destino = request.referrer
        if not destino or urlparse(destino).netloc != request.host:
            destino = url_for("inicio")
        return redirect(destino)


    # REFACTOR: leer números del formulario se repite en muchas rutas con el
    # mismo try/except. Crear una función leer_entero(nombre_campo) o usar WTForms.
    def leer_entero(campo):
        try:
            return int(request.form.get(campo, ""))
        except ValueError:
            raise ReglaNegocioError(f"El campo '{campo}' debe ser un número entero.")


    # ---------------------------------------------------------------- sesión (RF-01)
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            usuario = repo.buscar_usuario_por_nombre(request.form.get("nombre_usuario", ""))
            if usuario and usuario.autenticar(request.form.get("contrasena", "")):
                session.clear()
                session.permanent = True
                session["id_usuario"] = usuario.id_usuario
                return redirect(url_for("inicio"))
            flash("Usuario o contraseña incorrectos.", "error")  # RN-01
        return render_template("login.html")


    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))


    @app.route("/")
    @login_requerido
    def inicio():
        return redirect(url_for("caja" if usuario_actual().es_cajero() else "mesas"))


    # ---------------------------------------------------------------- mesero
    @app.route("/mesas")
    @login_requerido
    def mesas():
        usuario = usuario_actual()
        if not usuario.es_mesero():  # REFACTOR: chequeo de rol repetido
            abort(403)
        filas = [(m, repo.cuenta_activa_de_mesa(m.numero)) for m in repo.listar_mesas()]
        return render_template("mesas.html", filas=filas)


    @app.route("/mesas/<int:numero>/abrir", methods=["POST"])
    @login_requerido
    def abrir_cuenta(numero):
        """RF-03, RF-04."""
        cuenta = repo.abrir_cuenta(numero, usuario_actual(), leer_entero("comensales"))
        flash(f"Cuenta {cuenta.folio} abierta para la mesa {numero}.", "ok")
        return redirect(url_for("ver_cuenta", folio=cuenta.folio))


    @app.route("/cuentas/<int:folio>")
    @login_requerido
    def ver_cuenta(folio):
        usuario = usuario_actual()
        cuenta = repo.buscar_cuenta(folio)
        # El mesero solo ve las cuentas que él abrió (Sección 2, actor Mesero).
        # REFACTOR: esta misma comprobación ya existe dentro de Cuenta (_validar_duenio).
        if not usuario.es_mesero() or cuenta.mesero.id_usuario != usuario.id_usuario:
            abort(403)
        return render_template("cuenta_mesero.html", cuenta=cuenta, categorias=repo.listar_categorias())


    @app.route("/cuentas/<int:folio>/comensales", methods=["POST"])
    @login_requerido
    def cambiar_comensales(folio):
        """RF-04."""
        repo.buscar_cuenta(folio).registrar_comensales(leer_entero("comensales"), usuario_actual())
        return redirect(url_for("ver_cuenta", folio=folio))


    @app.route("/cuentas/<int:folio>/ordenes", methods=["POST"])
    @login_requerido
    def nueva_orden(folio):
        """RF-05."""
        repo.buscar_cuenta(folio).agregar_orden(usuario_actual())
        return redirect(url_for("ver_cuenta", folio=folio))


    @app.route("/cuentas/<int:folio>/ordenes/<int:numero>/productos", methods=["POST"])
    @login_requerido
    def agregar_producto(folio, numero):
        """RF-06."""
        cuenta = repo.buscar_cuenta(folio)
        producto = repo.buscar_producto(leer_entero("id_producto"))
        cuenta.agregar_producto(numero, producto, leer_entero("cantidad"),
                                request.form.get("nota", ""), usuario_actual())
        return redirect(url_for("ver_cuenta", folio=folio))


    @app.route("/cuentas/<int:folio>/productos/<int:id_detalle>/eliminar", methods=["POST"])
    @login_requerido
    def eliminar_producto(folio, id_detalle):
        """RF-07."""
        repo.buscar_cuenta(folio).eliminar_producto(id_detalle, usuario_actual())
        return redirect(url_for("ver_cuenta", folio=folio))


    @app.route("/cuentas/<int:folio>/productos/<int:id_detalle>/estado", methods=["POST"])
    @login_requerido
    def cambiar_estado_producto(folio, id_detalle):
        """RF-08."""
        repo.buscar_cuenta(folio).actualizar_estado_producto(
            id_detalle, request.form.get("estado", ""), usuario_actual())
        return redirect(url_for("ver_cuenta", folio=folio))


    @app.route("/cuentas/<int:folio>/solicitar", methods=["POST"])
    @login_requerido
    def solicitar_cuenta(folio):
        """RF-10."""
        repo.buscar_cuenta(folio).solicitar_cuenta(usuario_actual())
        flash(f"Cuenta {folio} enviada a caja.", "ok")
        return redirect(url_for("mesas"))


    # ---------------------------------------------------------------- cajero
    @app.route("/caja")
    @login_requerido
    def caja():
        if not usuario_actual().es_cajero():  # REFACTOR: chequeo de rol repetido
            abort(403)
        return render_template("caja.html", activas=repo.cuentas_activas(), cerradas=repo.cuentas_cerradas())


    @app.route("/caja/cuentas/<int:folio>")
    @login_requerido
    def caja_cuenta(folio):
        if not usuario_actual().es_cajero():  # REFACTOR: chequeo de rol repetido
            abort(403)
        return render_template("cuenta_caja.html", cuenta=repo.buscar_cuenta(folio))


    @app.route("/caja/cuentas/<int:folio>/propina", methods=["POST"])
    @login_requerido
    def aplicar_propina(folio):
        """RF-11."""
        tipo_propina = TIPOS_PROPINA.get(request.form.get("tipo"))
        if tipo_propina is None:
            raise ReglaNegocioError("Tipo de propina no válido.")
        ajuste = tipo_propina(request.form.get("valor", ""))
        repo.buscar_cuenta(folio).aplicar_propina(ajuste, usuario_actual())
        return redirect(url_for("caja_cuenta", folio=folio))


    # REFACTOR: las dos rutas de pago son casi iguales. Se podría tener una sola
    # ruta /pago con una "fábrica" que cree PagoEfectivo o PagoTarjeta según el método.
    @app.route("/caja/cuentas/<int:folio>/pago/efectivo", methods=["POST"])
    @login_requerido
    def pagar_efectivo(folio):
        """RF-12 (efectivo)."""
        cuenta = repo.buscar_cuenta(folio)
        pago = PagoEfectivo(usuario_actual(), request.form.get("monto_recibido", ""))
        if pago.procesar_cobro(cuenta):
            flash(f"Pago registrado. Cambio: {formato_dinero(pago.cambio)}", "ok")
            return redirect(url_for("ticket", folio=folio))
        flash("El efectivo recibido no cubre el total. La cuenta sigue por cobrar.", "error")
        return redirect(url_for("caja_cuenta", folio=folio))


    @app.route("/caja/cuentas/<int:folio>/pago/tarjeta", methods=["POST"])
    @login_requerido
    def pagar_tarjeta(folio):
        """RF-12 (tarjeta), RN-12."""
        cuenta = repo.buscar_cuenta(folio)
        pago = PagoTarjeta(usuario_actual(), terminal)
        if pago.procesar_cobro(cuenta):
            flash("Pago con tarjeta aprobado.", "ok")
            return redirect(url_for("ticket", folio=folio))
        flash("La terminal rechazó el cobro o no respondió en 30 s. "
            "Puedes reintentar o cobrar en efectivo.", "error")
        return redirect(url_for("caja_cuenta", folio=folio))


    @app.route("/caja/cuentas/<int:folio>/cancelar", methods=["POST"])
    @login_requerido
    def cancelar_cuenta(folio):
        """RF-13."""
        repo.buscar_cuenta(folio).cancelar(request.form.get("motivo", ""), usuario_actual())
        flash(f"Cuenta {folio} cancelada; la mesa quedó libre.", "ok")
        return redirect(url_for("caja"))


    @app.route("/caja/cuentas/<int:folio>/ticket")
    @login_requerido
    def ticket(folio):
        """RF-14, RN-14."""
        if not usuario_actual().es_cajero():  # REFACTOR: chequeo de rol repetido
            abort(403)
        cuenta = repo.buscar_cuenta(folio)
        if cuenta.pago is None:
            raise ReglaNegocioError("La cuenta no tiene un pago registrado (RN-14).")
        texto = GeneradorTicket().generar(cuenta.generar_resumen(), [cuenta.pago])
        return render_template("ticket.html", cuenta=cuenta, texto=texto)

    # ---------------------------------------------------------------- menú (RF-15)
    @app.route("/menu")
    @login_requerido
    def menu_admin():
        if not usuario_actual().es_cajero():  # REFACTOR: chequeo de rol repetido
            abort(403)
        return render_template("menu_admin.html", categorias=repo.listar_categorias())


    @app.route("/menu/productos", methods=["POST"])
    @login_requerido
    def crear_producto():
        if not usuario_actual().es_cajero():  # RN-15  REFACTOR: chequeo de rol repetido
            abort(403)
        repo.crear_producto(request.form.get("nombre"), request.form.get("precio"),
                            leer_entero("id_categoria"), "disponible" in request.form)
        flash("Producto creado.", "ok")
        return redirect(url_for("menu_admin"))


    @app.route("/menu/productos/<int:id_producto>", methods=["POST"])
    @login_requerido
    def actualizar_producto(id_producto):
        if not usuario_actual().es_cajero():  # RN-15  REFACTOR: chequeo de rol repetido
            abort(403)
        producto = repo.buscar_producto(id_producto)
        producto.actualizar_datos(request.form.get("nombre"), request.form.get("precio"))
        producto.marcar_disponible("disponible" in request.form)
        flash("Producto actualizado.", "ok")
        return redirect(url_for("menu_admin"))

    return app

app = crear_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")