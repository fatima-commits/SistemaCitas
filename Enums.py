"""Tipos enumerados del sistema (Sección 8 del documento)."""
from enum import Enum


class RolUsuario(Enum):
    MESERO = "mesero"
    CAJERO = "cajero"
    # REFACTOR: si SUP-05 resulta falso, aquí se agregaría GERENTE.


class EstadoMesa(Enum):
    LIBRE = "libre"
    OCUPADA = "ocupada"


class EstadoCuenta(Enum):
    ABIERTA = "abierta"
    POR_COBRAR = "por cobrar"
    PAGADA = "pagada"
    CANCELADA = "cancelada"


class EstadoDetalleOrden(Enum):
    PENDIENTE = "pendiente"
    EN_PREPARACION = "en preparación"
    ENTREGADO = "entregado"


class MetodoPago(Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"