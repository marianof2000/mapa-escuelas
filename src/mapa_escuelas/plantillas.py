# -*- coding: utf-8 -*-
"""Acceso centralizado a las plantillas de los controles del mapa."""

from functools import cache
from pathlib import Path


PLANTILLAS_DIR = Path(__file__).with_name("templates")


@cache
def cargar_plantilla(nombre: str) -> str:
    """Carga una plantilla incluida en el paquete y conserva el resultado."""
    return (PLANTILLAS_DIR / nombre).read_text(encoding="utf-8")
