from decimal import ROUND_HALF_UP, Decimal


def redondear(valor):
    """RNF-04: todos los montos a 2 decimales."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
