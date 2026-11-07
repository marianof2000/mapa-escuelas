# -*- coding: utf-8 -*-
"""Composición del mapa interactivo de escuelas de Dolores."""
import folium
from folium import plugins
from folium.plugins import MiniMap, MousePosition
import pandas as pd
from .controles import (
    _agregar_buscador_escuelas, _agregar_estilos_selector_padrones,
    _agregar_selector_padrones, _crear_capa_escuelas,
)
from .datos import _anio_para_ordenar_padron
from .popups import _agregar_estilos_popups

def crear_mapa(
    escuelas_por_padron: dict[str, pd.DataFrame],
    limite_dolores: str,
) -> folium.Map:
    """Construye el mapa interactivo de escuelas de Dolores.

    Precondiciones:
        ``escuelas_por_padron`` es un diccionario de ``DataFrame`` que cumple
        el contrato de :func:`_crear_capa_escuelas`; ``limite_dolores``
        contiene GeoJSON valido.
    Postcondiciones:
        Retorna un nuevo ``folium.Map`` con limite, capas, minimapa y visor de
        coordenadas; agrega el selector cuando existe al menos una capa y no
        modifica los argumentos recibidos.
    """
    mapa = folium.Map(
        location=[-36.316076, -57.674351],
        zoom_start=10,
        control_scale=True,
        min_lat=-37,
        max_lat=-36,
        min_lon=-58,
        max_lon=-57,
        zoom_control=False,
    )
    folium.GeoJson(limite_dolores).add_to(mapa)

    capas = {}
    resumenes = {}
    popup_html_cache = {}
    registros_busqueda = []
    padrones_ordenados = sorted(
        escuelas_por_padron.items(),
        key=lambda item: _anio_para_ordenar_padron(item[0]),
        reverse=True,
    )
    for nombre, escuelas in padrones_ordenados:
        capa = _crear_capa_escuelas(
            escuelas,
            nombre,
            popup_html_cache,
            registros_busqueda,
        )
        capa.add_to(mapa)
        capas[nombre] = capa
        ambitos = escuelas["Ámbito"].astype(str).str.strip().str.casefold()
        resumenes[nombre] = {
            "rurales": int(ambitos.eq("rural").sum()),
            "urbanas": int(ambitos.eq("urbano").sum()),
        }

    if capas:
        nombre_inicial = next(
            (
                nombre
                for nombre in capas
                if _anio_para_ordenar_padron(nombre) == 2026
            ),
            next(iter(capas)),
        )
        _agregar_estilos_selector_padrones(mapa)
        _agregar_estilos_popups(mapa)
        _agregar_selector_padrones(mapa, capas, nombre_inicial, resumenes)
        _agregar_buscador_escuelas(mapa, registros_busqueda)

    MiniMap().add_to(mapa)

    formatter = "function(num) {return L.Util.formatNum(num, 3) + ' &deg; ';};"
    MousePosition(
        position="topright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=20,
        prefix="Coordenadas:",
        lat_formatter=formatter,
        lng_formatter=formatter,
    ).add_to(mapa)

    return mapa
