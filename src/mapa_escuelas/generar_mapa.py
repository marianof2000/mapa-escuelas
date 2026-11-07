# -*- coding: utf-8 -*-
"""Genera el mapa interactivo de escuelas primarias de Dolores."""

import logging

from .config import OUTPUT_PATH
from .datos import (
    cargar_escuelas_por_padron_csv,
    cargar_limite_dolores,
)
from .mapa import crear_mapa


def main() -> None:
    """Genera y guarda el mapa interactivo usando las fuentes configuradas.

    Precondiciones:
        Las rutas configuradas contienen el limite y los CSV compatibles con
        sus respectivas funciones de carga, y ``OUTPUT_PATH`` es escribible.
    Postcondiciones:
        Guarda el mapa en ``OUTPUT_PATH``, informa la ruta por salida estandar
        y retorna ``None``.
    """
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    limite_dolores = cargar_limite_dolores()
    escuelas_por_padron = cargar_escuelas_por_padron_csv()
    mapa = crear_mapa(escuelas_por_padron, limite_dolores)
    mapa.save(OUTPUT_PATH)
    print(f"Mapa generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
