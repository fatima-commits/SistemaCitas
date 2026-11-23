"""Guarda todos los objetos en memoria y carga datos de ejemplo.

Usuarios de prueba (contraseña 1234): mesero1, mesero2, cajero1.
"""
import itertools

from Cuenta import Cuenta
from Enums import EstadoCuenta, RolUsuario
from Errores import ReglaNegocioError
from Mesa import Mesa
from Menu import Categoria, Producto
from Usuario import Usuario


# REFACTOR: todo vive en memoria; al reiniciar el servidor se pierde todo.
# DEP-02 pide un servidor con base de datos. Definir una interfaz Repositorio
# y crear una implementación con SQLite/SQLAlchemy sin tocar el resto del código.
# REFACTOR: no es seguro con varios hilos a la vez (RNF-01: 20 dispositivos).
# Agregar un threading.Lock o usar la base de datos.
class RepositorioMemoria:
    def __init__(self):
        self._usuarios = {}
        self._mesas = {}
        self._categorias = {}
        self._productos = {}
        self._cuentas = {}
        self._folios = itertools.count(1)
        self._ids_producto = itertools.count(1)
        self._cargar_datos_iniciales()

    def _cargar_datos_iniciales(self):
        # REFACTOR: datos de ejemplo mezclados con el repositorio. Moverlos a un
        # script aparte (semilla.py) o a un archivo JSON.
        for u in (
            Usuario(1, "Ana Mesera", "mesero1", "1234", RolUsuario.MESERO),
            Usuario(2, "Luis Mesero", "mesero2", "1234", RolUsuario.MESERO),
            Usuario(3, "Carla Cajera", "cajero1", "1234", RolUsuario.CAJERO),
        ):
            self._usuarios[u.id_usuario] = u

        for numero in range(1, 41):
            self._mesas[numero] = Mesa(numero, capacidad=[2, 4, 6, 8][numero % 4])

        nombres = ["Entradas", "Platos fuertes", "Bebidas", "Postres"]
        for posicion, nombre in enumerate(nombres, start=1):
            self._categorias[posicion] = Categoria(posicion, nombre, posicion)

        ejemplo = [
            ("Guacamole", "95.00", 1, True),
            ("Sopa de tortilla", "85.00", 1, True),
            ("Tacos al pastor (3)", "120.00", 2, True),
            ("Enchiladas suizas", "145.00", 2, True),
            ("Arrachera", "260.00", 2, False),
            ("Agua de horchata", "40.00", 3, True),
            ("Refresco", "35.00", 3, True),
            ("Flan napolitano", "60.00", 4, True),
        ]
        for nombre, precio, id_cat, disponible in ejemplo:
            self.crear_producto(nombre, precio, id_cat, disponible)

    # ---------- usuarios ----------
    def buscar_usuario_por_nombre(self, nombre_usuario):
        for u in self._usuarios.values():
            if u.nombre_usuario == nombre_usuario:
                return u
        return None

    def buscar_usuario(self, id_usuario):
        return self._usuarios.get(id_usuario)

    # ---------- mesas ----------
    def listar_mesas(self):
        return list(self._mesas.values())

    def buscar_mesa(self, numero):
        mesa = self._mesas.get(numero)
        if mesa is None:
            raise ReglaNegocioError("La mesa no existe.")
        return mesa

    # ---------- cuentas ----------
    def abrir_cuenta(self, numero_mesa, mesero, numero_comensales):
        """RF-03."""
        # REFACTOR: el folio se consume aunque la Cuenta falle al crearse
        # (p. ej. comensales inválidos), así que quedan huecos en los folios.
        # Validar antes o tomar el folio solo si la creación tuvo éxito.
        cuenta = Cuenta(next(self._folios), self.buscar_mesa(numero_mesa), mesero, numero_comensales)
        self._cuentas[cuenta.folio] = cuenta
        return cuenta

    def buscar_cuenta(self, folio):
        cuenta = self._cuentas.get(folio)
        if cuenta is None:
            raise ReglaNegocioError("La cuenta no existe.")
        return cuenta

    def cuenta_activa_de_mesa(self, numero_mesa):
        for c in self._cuentas.values():
            if c.mesa.numero == numero_mesa and c.estado in (EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR):
                return c
        return None

    # REFACTOR: los tres métodos siguientes recorren todas las cuentas con un
    # filtro casi igual. Unificar en uno solo: cuentas(estados=..., mesero=...).
    def cuentas_de_mesero(self, mesero):
        return [
            c for c in self._cuentas.values()
            if c.mesero.id_usuario == mesero.id_usuario
            and c.estado in (EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR)
        ]

    def cuentas_activas(self):
        return [c for c in self._cuentas.values() if c.estado in (EstadoCuenta.ABIERTA, EstadoCuenta.POR_COBRAR)]

    def cuentas_cerradas(self):
        return [c for c in self._cuentas.values() if c.estado in (EstadoCuenta.PAGADA, EstadoCuenta.CANCELADA)]

    # ---------- menú ----------
    def listar_categorias(self):
        return sorted(self._categorias.values(), key=lambda c: c.posicion)

    def buscar_categoria(self, id_categoria):
        categoria = self._categorias.get(id_categoria)
        if categoria is None:
            raise ReglaNegocioError("La categoría no existe.")
        return categoria

    def buscar_producto(self, id_producto):
        producto = self._productos.get(id_producto)
        if producto is None:
            raise ReglaNegocioError("El producto no existe.")
        return producto

    def crear_producto(self, nombre, precio, id_categoria, disponible=True):
        """RF-15."""
        producto = Producto(next(self._ids_producto), nombre, precio,
                            self.buscar_categoria(id_categoria), disponible)
        self._productos[producto.id_producto] = producto
        return producto