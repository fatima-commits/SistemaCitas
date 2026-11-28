"""Clase Usuario (Tarjeta CRC 1). Mesero y cajero son la misma clase con distinto rol."""
from werkzeug.security import check_password_hash, generate_password_hash

from Enums import RolUsuario


class Usuario:
    def __init__(self, id_usuario, nombre, nombre_usuario, contrasena, rol):
        self._id_usuario = id_usuario
        self._nombre = nombre
        self._nombre_usuario = nombre_usuario
        # RNF-02: hash con sal (werkzeug genera la sal automáticamente).
        self._contrasena_cifrada = generate_password_hash(contrasena)
        self._rol = rol

    @property
    def id_usuario(self):
        return self._id_usuario

    @property
    def nombre(self):
        return self._nombre

    @property
    def nombre_usuario(self):
        return self._nombre_usuario

    @property
    def rol(self):
        return self._rol

    def autenticar(self, contrasena):
        """RF-01, RN-01."""
        return check_password_hash(self._contrasena_cifrada, contrasena)

    def validar_rol(self, rol_requerido):
        """RN-06, RN-13, RN-15."""
        return self._rol == rol_requerido

    # REFACTOR: estos dos métodos son atajos que se repiten por todo el código
    # (usuario.validar_rol(RolUsuario.MESERO)). Valorar si conviene dejarlos
    # o quitar validar_rol y usar solo estos.
    def es_mesero(self):
        return self._rol == RolUsuario.MESERO

    def es_cajero(self):
        return self._rol == RolUsuario.CAJERO
