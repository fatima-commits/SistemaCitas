"""Clases Categoria y Producto. El "Menú" es el conjunto de productos (Sección 8)."""
from decimal import Decimal, InvalidOperation

from Errores import ReglaNegocioError


class Categoria:
    def __init__(self, id_categoria, nombre, posicion):
        self._id_categoria = id_categoria
        self._nombre = nombre
        self._posicion = posicion
        self._productos = []

    @property
    def id_categoria(self):
        return self._id_categoria

    @property
    def nombre(self):
        return self._nombre

    @property
    def posicion(self):
        return self._posicion

    @property
    def productos(self):
        return list(self._productos)

    def filtrar_disponibles(self):
        """RF-02, RN-02."""
        return [p for p in self._productos if p.disponible]

    def asignar_producto(self, producto):
        """RF-15."""
        if producto not in self._productos:
            self._productos.append(producto)


class Producto:
    def __init__(self, id_producto, nombre, precio, categoria, disponible=True):
        self._id_producto = id_producto
        self._nombre = ""
        self._precio = Decimal("0.00")
        self.actualizar_datos(nombre, precio)
        self._disponible = bool(disponible)
        self._categoria = categoria
        categoria.asignar_producto(self)

    @property
    def id_producto(self):
        return self._id_producto

    @property
    def nombre(self):
        return self._nombre

    @property
    def precio(self):
        """Precio con IVA incluido (RES-03, RN-09)."""
        return self._precio

    @property
    def disponible(self):
        return self._disponible

    @property
    def categoria(self):
        return self._categoria

    def actualizar_datos(self, nombre, precio):
        """RF-15, RN-15: nombre obligatorio y precio válido (> 0).

        Nota: RN-15 dice "solo el cajero"; esa validación está en app.py.
        """
        # REFACTOR: la validación de rol (RN-15) vive en la ruta y no aquí,
        # a diferencia de Cuenta, que sí recibe al usuario. Hacerlo consistente.
        nombre = (nombre or "").strip()
        if not nombre:
            raise ReglaNegocioError("El producto debe tener nombre (RN-15).")
        try:
            precio = Decimal(str(precio))
        except InvalidOperation:
            raise ReglaNegocioError("El precio no es válido (RN-15).")
        if not precio.is_finite() or precio <= 0:
            raise ReglaNegocioError("El precio debe ser mayor que cero (RN-15).")
        self._nombre = nombre
        self._precio = precio.quantize(Decimal("0.01"))

    def marcar_disponible(self, disponible):
        """RF-15."""
        self._disponible = bool(disponible)

    # REFACTOR: no hay forma de cambiar la categoría de un producto existente.