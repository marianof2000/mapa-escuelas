# -*- coding: utf-8 -*-
"""Acceso centralizado a las plantillas de los controles del mapa."""

from functools import cache
from pathlib import Path


PLANTILLAS_DIR = Path(__file__).with_name("templates")


@cache
def cargar_plantilla(nombre: str) -> str:
    """Carga una plantilla incluida en el paquete y conserva el resultado.

    Precondiciones:
        ``nombre`` identifica un archivo UTF-8 existente dentro de
        ``PLANTILLAS_DIR``.
    Postcondiciones:
        Retorna el contenido completo de la plantilla y conserva en cache el
        resultado para invocaciones posteriores con el mismo nombre.
    """
    return (PLANTILLAS_DIR / nombre).read_text(encoding="utf-8")
