"""Casos CV-MESA-01 a CV-MESA-06 (antes estaban dentro de Mesa.py)."""
import pytest

from Enums import EstadoMesa
from Errores import ReglaNegocioError
from Mesa import (
    CAPACIDAD_MESA_MAXIMA,
    CAPACIDAD_MESA_MINIMA,
    NUMERO_MESA_MAXIMO,
    NUMERO_MESA_MINIMO,
    Mesa,
)


def test_limites_validos():
    Mesa(NUMERO_MESA_MINIMO, CAPACIDAD_MESA_MINIMA)
    Mesa(NUMERO_MESA_MAXIMO, CAPACIDAD_MESA_MAXIMA)


@pytest.mark.parametrize("numero", [NUMERO_MESA_MINIMO - 1, NUMERO_MESA_MAXIMO + 1])
def test_numero_fuera_de_limites(numero):
    with pytest.raises(ReglaNegocioError):
        Mesa(numero, 4)


@pytest.mark.parametrize("capacidad", [CAPACIDAD_MESA_MINIMA - 1, CAPACIDAD_MESA_MAXIMA + 1])
def test_capacidad_fuera_de_limites(capacidad):
    with pytest.raises(ReglaNegocioError):
        Mesa(1, capacidad)


def test_cambio_de_estado():
    mesa = Mesa(1, 4)
    mesa.ocupar()
    assert mesa.estado == EstadoMesa.OCUPADA
    mesa.liberar()
    assert mesa.estado == EstadoMesa.LIBRE


def test_ocupar_dos_veces():
    mesa = Mesa(1, 4)
    mesa.ocupar()
    with pytest.raises(ReglaNegocioError):
        mesa.ocupar()
