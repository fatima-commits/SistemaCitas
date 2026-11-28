"""Plantillas HTML (Jinja2) guardadas como texto para que todo quede en Python.

REFACTOR: mover cada plantilla a su propio archivo dentro de una carpeta
templates/ y el CSS a static/estilos.css. Así Flask las encuentra solo y se
puede quitar el DictLoader de app.py.
"""

BASE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CuentaMesa</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; color: #222; }
  nav { background: #263238; color: #fff; padding: .7rem 1rem; display: flex; gap: 1rem; align-items: center; }
  nav a { color: #fff; } nav .der { margin-left: auto; }
  main { max-width: 1000px; margin: 1rem auto; padding: 0 1rem; }
  .caja { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
  table { width: 100%; border-collapse: collapse; } td, th { padding: .4rem; border-bottom: 1px solid #ddd; text-align: left; }
  .num { text-align: right; }
  .msg { padding: .6rem 1rem; border-radius: 6px; margin-bottom: .5rem; }
  .ok { background: #e0f2e9; } .error { background: #fde2e1; }
  button, input, select { font-size: 1rem; padding: .35rem .6rem; }
  .rejilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .6rem; }
  .libre { border-left: 6px solid #2e7d32; } .ocupada { border-left: 6px solid #c62828; }
  form.linea { display: inline; }
  @media print { nav, .no-imprimir { display: none; } body { background: #fff; } }
</style>
</head>
<body>
{% if usuario %}
<nav>
  <strong>CuentaMesa</strong>
  {% if usuario.es_mesero() %}<a href="{{ url_for('mesas') }}">Mesas</a>{% endif %}
  {% if usuario.es_cajero() %}<a href="{{ url_for('caja') }}">Caja</a> <a href="{{ url_for('menu_admin') }}">Menú</a>{% endif %}
  <span class="der">{{ usuario.nombre }} ({{ usuario.rol.value }}) · <a href="{{ url_for('logout') }}">Salir</a></span>
</nav>
{% endif %}
<main>
  {% for categoria, mensaje in get_flashed_messages(with_categories=true) %}
    <div class="msg {{ categoria }}">{{ mensaje }}</div>
  {% endfor %}
  {% block contenido %}{% endblock %}
</main>
</body>
</html>"""

LOGIN = r"""{% extends "base.html" %}
{% block contenido %}
<div class="caja" style="max-width:340px;margin:3rem auto">
  <h2>Iniciar sesión</h2>
  <form method="post">
    <p><input name="nombre_usuario" placeholder="Usuario" required autofocus></p>
    <p><input name="contrasena" type="password" placeholder="Contraseña" required></p>
    <button>Entrar</button>
  </form>
  <small>Prueba: mesero1 / cajero1, contraseña 1234</small>
</div>
{% endblock %}"""

MESAS = r"""{% extends "base.html" %}
{% block contenido %}
<h2>Mesas</h2>
<div class="rejilla">
{% for mesa, cuenta in filas %}
  <div class="caja {{ mesa.estado.value }}">
    <strong>Mesa {{ mesa.numero }}</strong><br><small>Capacidad {{ mesa.capacidad }}</small><br>
    {% if mesa.esta_libre() %}
      <form method="post" action="{{ url_for('abrir_cuenta', numero=mesa.numero) }}">
        <input name="comensales" type="number" min="1" max="{{ mesa.capacidad }}" value="1" style="width:4rem">
        <button>Abrir</button>
      </form>
    {% elif cuenta and cuenta.mesero.id_usuario == usuario.id_usuario %}
      <a href="{{ url_for('ver_cuenta', folio=cuenta.folio) }}">Cuenta {{ cuenta.folio }}</a> ({{ cuenta.estado.value }})
    {% else %}
      <small>Ocupada{% if cuenta %} por {{ cuenta.mesero.nombre }}{% endif %}</small>
    {% endif %}
  </div>
{% endfor %}
</div>
{% endblock %}"""

# REFACTOR: la tabla de productos de la cuenta está repetida (con ligeras
# diferencias) en CUENTA_MESERO y CUENTA_CAJA. Crear una macro de Jinja.
CUENTA_MESERO = r"""{% extends "base.html" %}
{% block contenido %}
{% set abierta = cuenta.estado == EstadoCuenta.ABIERTA %}
<h2>Cuenta {{ cuenta.folio }} · Mesa {{ cuenta.mesa.numero }} · {{ cuenta.estado.value }}</h2>

<div class="caja">
  <form method="post" action="{{ url_for('cambiar_comensales', folio=cuenta.folio) }}">
    Comensales: <input name="comensales" type="number" min="1" max="{{ cuenta.mesa.capacidad }}"
      value="{{ cuenta.numero_comensales }}" style="width:4rem" {% if not abierta %}disabled{% endif %}>
    {% if abierta %}<button>Guardar</button>{% endif %}
  </form>
</div>

<details class="caja">
  <summary><strong>Menú disponible</strong></summary>
  {% for cat in categorias %}
    <h4>{{ cat.nombre }}</h4>
    <ul>{% for p in cat.filtrar_disponibles() %}<li>{{ p.nombre }} — {{ p.precio|dinero }}</li>{% endfor %}</ul>
  {% endfor %}
</details>

{% for orden in cuenta.ordenes %}
<div class="caja">
  <h3>Orden {{ orden.numero_en_cuenta }} <small>{{ orden.fecha_hora.strftime('%H:%M') }}</small></h3>
  <table>
    <tr><th>Cant.</th><th>Producto</th><th>Nota</th><th class="num">Importe</th><th>Estado</th><th></th></tr>
    {% for d in orden.detalles %}
    <tr>
      <td>{{ d.cantidad }}</td><td>{{ d.producto.nombre }}</td><td>{{ d.nota }}</td>
      <td class="num">{{ d.calcular_importe()|dinero }}</td>
      <td>
        <form class="linea" method="post" action="{{ url_for('cambiar_estado_producto', folio=cuenta.folio, id_detalle=d.id_detalle) }}">
          <select name="estado" onchange="this.form.submit()">
            {% for e in EstadoDetalleOrden %}<option value="{{ e.value }}" {% if e == d.estado %}selected{% endif %}>{{ e.value }}</option>{% endfor %}
          </select>
        </form>
      </td>
      <td>{% if abierta %}
        <form class="linea" method="post" action="{{ url_for('eliminar_producto', folio=cuenta.folio, id_detalle=d.id_detalle) }}"><button>Quitar</button></form>
      {% endif %}</td>
    </tr>
    {% endfor %}
  </table>
  {% if abierta %}
  <form method="post" action="{{ url_for('agregar_producto', folio=cuenta.folio, numero=orden.numero_en_cuenta) }}" style="margin-top:.6rem">
    <select name="id_producto" required>
      {% for cat in categorias %}<optgroup label="{{ cat.nombre }}">
        {% for p in cat.filtrar_disponibles() %}<option value="{{ p.id_producto }}">{{ p.nombre }} ({{ p.precio|dinero }})</option>{% endfor %}
      </optgroup>{% endfor %}
    </select>
    <input name="cantidad" type="number" min="1" value="1" style="width:4rem">
    <input name="nota" placeholder="Nota (opcional)">
    <button>Agregar</button>
  </form>
  {% endif %}
</div>
{% endfor %}

{% if abierta %}
<form method="post" action="{{ url_for('nueva_orden', folio=cuenta.folio) }}"><button>+ Nueva orden</button></form>
{% endif %}

<div class="caja" style="margin-top:1rem">
  <table>
    <tr><td>Subtotal</td><td class="num">{{ cuenta.calcular_subtotal()|dinero }}</td></tr>
    <tr><td>IVA 16%</td><td class="num">{{ cuenta.calcular_iva()|dinero }}</td></tr>
    <tr><th>Total consumo</th><th class="num">{{ cuenta.calcular_consumo()|dinero }}</th></tr>
  </table>
  {% if abierta %}
  <form method="post" action="{{ url_for('solicitar_cuenta', folio=cuenta.folio) }}" style="margin-top:.6rem">
    <button>Solicitar cuenta</button>
  </form>
  {% endif %}
</div>
{% endblock %}"""

CAJA = r"""{% extends "base.html" %}
{% block contenido %}
<h2>Caja</h2>
<div class="caja">
  <h3>Cuentas activas</h3>
  <table>
    <tr><th>Folio</th><th>Mesa</th><th>Mesero</th><th>Estado</th><th class="num">Total</th><th></th></tr>
    {% for c in activas %}
    <tr><td>{{ c.folio }}</td><td>{{ c.mesa.numero }}</td><td>{{ c.mesero.nombre }}</td><td>{{ c.estado.value }}</td>
        <td class="num">{{ c.calcular_total_a_pagar()|dinero }}</td>
        <td><a href="{{ url_for('caja_cuenta', folio=c.folio) }}">Abrir</a></td></tr>
    {% else %}<tr><td colspan="6">No hay cuentas activas.</td></tr>{% endfor %}
  </table>
</div>
<div class="caja">
  <h3>Cuentas cerradas</h3>
  <table>
    {% for c in cerradas %}
    <tr><td>{{ c.folio }}</td><td>Mesa {{ c.mesa.numero }}</td><td>{{ c.estado.value }}</td>
        <td>{% if c.pago %}<a href="{{ url_for('ticket', folio=c.folio) }}">Ticket</a>{% else %}{{ c.motivo_cancelacion }}{% endif %}</td></tr>
    {% else %}<tr><td>Ninguna todavía.</td></tr>{% endfor %}
  </table>
</div>
{% endblock %}"""

CUENTA_CAJA = r"""{% extends "base.html" %}
{% block contenido %}
{% set por_cobrar = cuenta.estado == EstadoCuenta.POR_COBRAR %}
<h2>Cuenta {{ cuenta.folio }} · Mesa {{ cuenta.mesa.numero }} · {{ cuenta.estado.value }}</h2>
<div class="caja">
  <table>
    <tr><th>Cant.</th><th>Producto</th><th class="num">Importe</th></tr>
    {% for orden in cuenta.ordenes %}{% for d in orden.detalles %}
      <tr><td>{{ d.cantidad }}</td><td>{{ d.producto.nombre }}</td><td class="num">{{ d.calcular_importe()|dinero }}</td></tr>
    {% endfor %}{% endfor %}
    <tr><td></td><td>Subtotal</td><td class="num">{{ cuenta.calcular_subtotal()|dinero }}</td></tr>
    <tr><td></td><td>IVA 16%</td><td class="num">{{ cuenta.calcular_iva()|dinero }}</td></tr>
    <tr><td></td><td>Consumo</td><td class="num">{{ cuenta.calcular_consumo()|dinero }}</td></tr>
    <tr><td></td><td>Propina</td><td class="num">{{ cuenta.propina|dinero }}</td></tr>
    <tr><th></th><th>Total a pagar</th><th class="num">{{ cuenta.calcular_total_a_pagar()|dinero }}</th></tr>
  </table>
</div>

{% if por_cobrar %}
<div class="caja">
  <h3>Propina</h3>
  <form method="post" action="{{ url_for('aplicar_propina', folio=cuenta.folio) }}">
    <input name="valor" type="number" step="0.01" min="0" value="0" style="width:6rem">
    <select name="tipo"><option value="porcentaje">%</option><option value="fijo">$ fijo</option></select>
    <button>Aplicar</button>
  </form>
</div>
<div class="caja">
  <h3>Cobrar</h3>
  <form method="post" action="{{ url_for('pagar_efectivo', folio=cuenta.folio) }}">
    Efectivo recibido: <input name="monto_recibido" type="number" step="0.01" min="0" required style="width:8rem">
    <button>Cobrar en efectivo</button>
  </form>
  <form method="post" action="{{ url_for('pagar_tarjeta', folio=cuenta.folio) }}" style="margin-top:.6rem">
    <button>Cobrar con tarjeta ({{ cuenta.calcular_total_a_pagar()|dinero }})</button>
  </form>
</div>
{% endif %}

{% if cuenta.estado in (EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR) %}
<div class="caja">
  <h3>Cancelar cuenta</h3>
  <form method="post" action="{{ url_for('cancelar_cuenta', folio=cuenta.folio) }}">
    <input name="motivo" placeholder="Motivo (obligatorio)" style="width:60%">
    <button>Cancelar</button>
  </form>
</div>
{% endif %}
{% if cuenta.pago %}<a href="{{ url_for('ticket', folio=cuenta.folio) }}">Ver ticket</a>{% endif %}
{% endblock %}"""

TICKET = r"""{% extends "base.html" %}
{% block contenido %}
<div class="caja" style="max-width:420px;margin:auto">
  <pre>{{ texto }}</pre>
  <button class="no-imprimir" onclick="window.print()">Imprimir</button>
  <a class="no-imprimir" href="{{ url_for('caja') }}">Volver a caja</a>
</div>
{% endblock %}"""

MENU_ADMIN = r"""{% extends "base.html" %}
{% block contenido %}
<h2>Menú</h2>
<div class="caja">
  <h3>Nuevo producto</h3>
  <form method="post" action="{{ url_for('crear_producto') }}">
    <input name="nombre" placeholder="Nombre">
    <input name="precio" type="number" step="0.01" placeholder="Precio con IVA" style="width:8rem">
    <select name="id_categoria">{% for c in categorias %}<option value="{{ c.id_categoria }}">{{ c.nombre }}</option>{% endfor %}</select>
    <label><input type="checkbox" name="disponible" checked> Disponible</label>
    <button>Crear</button>
  </form>
</div>
{% for c in categorias %}
<div class="caja">
  <h3>{{ c.nombre }}</h3>
  {% for p in c.productos %}
  <form method="post" action="{{ url_for('actualizar_producto', id_producto=p.id_producto) }}" style="margin-bottom:.4rem">
    <input name="nombre" value="{{ p.nombre }}">
    <input name="precio" type="number" step="0.01" value="{{ p.precio }}" style="width:8rem">
    <label><input type="checkbox" name="disponible" {% if p.disponible %}checked{% endif %}> Disponible</label>
    <button>Guardar</button>
  </form>
  {% endfor %}
</div>
{% endfor %}
{% endblock %}"""

PLANTILLAS = {
    "base.html": BASE,
    "login.html": LOGIN,
    "mesas.html": MESAS,
    "cuenta_mesero.html": CUENTA_MESERO,
    "caja.html": CAJA,
    "cuenta_caja.html": CUENTA_CAJA,
    "ticket.html": TICKET,
    "menu_admin.html": MENU_ADMIN,
}
