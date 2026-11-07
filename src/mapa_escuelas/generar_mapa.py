# -*- coding: utf-8 -*-
"""Genera el mapa interactivo de escuelas primarias de Dolores."""

import logging
from pathlib import Path

import folium

from .config import OUTPUT_PATH
from .datos import (
    cargar_escuelas_por_padron_csv,
    cargar_limite_dolores,
)
from .mapa import crear_mapa


def _compactar_html_generado(html: str) -> str:
    """Elimina lineas vacias e indentacion del HTML generado por Folium.

    Precondiciones:
        ``html`` contiene un documento generado por Folium donde la sangria al
        comienzo de cada linea no representa contenido visual significativo.
    Postcondiciones:
        Retorna una nueva cadena sin lineas vacias ni espacios iniciales, con
        un unico salto de linea final; no modifica la cadena recibida.
    """
    lineas_compactas = (
        linea.lstrip()
        for linea in html.splitlines()
        if linea.strip()
    )
    return "\n".join(lineas_compactas) + "\n"


def _guardar_mapa_compacto(mapa: folium.Map, output_path: Path) -> None:
    """Guarda un mapa Folium y compacta el HTML resultante.

    Precondiciones:
        ``mapa`` puede serializarse como HTML y el directorio padre de
        ``output_path`` existe y permite escritura.
    Postcondiciones:
        Escribe en ``output_path`` el mapa completo sin lineas vacias ni
        indentacion inicial innecesaria y retorna ``None``.
    """
    mapa.save(output_path)
    html = output_path.read_text(encoding="utf-8")
    output_path.write_text(_compactar_html_generado(html), encoding="utf-8")


def main() -> None:
    """Genera y guarda el mapa interactivo usando las fuentes configuradas.

    Precondiciones:
        Las rutas configuradas contienen el limite y los CSV compatibles con
        sus respectivas funciones de carga, y ``OUTPUT_PATH`` es escribible.
    Postcondiciones:
        Guarda el mapa compactado en ``OUTPUT_PATH``, informa la ruta por
        salida estandar y retorna ``None``.
    """
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    limite_dolores = cargar_limite_dolores()
    escuelas_por_padron = cargar_escuelas_por_padron_csv()
    mapa = crear_mapa(escuelas_por_padron, limite_dolores)
    _guardar_mapa_compacto(mapa, OUTPUT_PATH)
    print(f"Mapa generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
