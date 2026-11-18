class ReglaNegocioError(Exception):
    """Se lanza cuando una operación viola una regla de negocio (RN-xx).

    La app la atrapa y muestra el mensaje al usuario.
    """
    # REFACTOR: todas las violaciones usan la misma excepción. Se podrían crear
    # subclases (PermisoDenegadoError, EstadoInvalidoError, ValorInvalidoError)
    # para responder distinto a cada una (p. ej. 403 en permisos).