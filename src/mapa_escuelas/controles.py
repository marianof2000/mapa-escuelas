# -*- coding: utf-8 -*-
"""Capas y conexión de los controles interactivos con Folium."""

from html import escape
import json

import branca
import folium
from folium import plugins
import pandas as pd

from .config import URBANAS_URL
from .datos import _normalizar_cueanexo
from .plantillas import cargar_plantilla
from .popups import _crear_popup_desde_html, _crear_popup_html


def _crear_capa_escuelas(
    escuelas: pd.DataFrame,
    nombre: str,
    popup_html_cache: dict[tuple[str, str, str, str, str], str],
    registros_busqueda: list[dict[str, str]],
) -> plugins.MarkerCluster:
    """Crea una capa de marcadores para un conjunto de escuelas.

    Precondiciones:
        ``escuelas`` contiene nombre, Cueanexo, Domicilio, Ambito, latitud y
        longitud; ``popup_html_cache`` es un diccionario,
        ``registros_busqueda`` es una lista mutable y ``nombre`` identifica
        la capa.
    Postcondiciones:
        Retorna un nuevo ``MarkerCluster`` con un marcador por fila y agrega al
        cache el HTML faltante y un registro de busqueda por marcador, sin
        modificar ``escuelas``.
    """
    capa = plugins.MarkerCluster(name=nombre, control=False)
    columnas_no_indexadas = {"historia", "link", "latitud", "longitud"}
    for escuela in escuelas.itertuples(index=False):
        ambito = getattr(escuela, "Ámbito")
        es_rural = str(ambito).strip().casefold() == "rural"
        color = "orange" if es_rural else "lightblue"
        cueanexo = _normalizar_cueanexo(escuela.Cueanexo)
        link = (
            str(getattr(escuela, "link", "")).strip()
            if es_rural
            else URBANAS_URL
        )
        historia = ""
        if es_rural:
            historia = str(
                getattr(escuela, "historia", "Historia no disponible.")
            ).strip() or "Historia no disponible."
        popup_cache_key = (
            cueanexo,
            str(escuela.Domicilio),
            str(ambito),
            link,
            historia,
        )
        if popup_cache_key not in popup_html_cache:
            popup_html_cache[popup_cache_key] = _crear_popup_html(
                escuela.nombre,
                escuela.Domicilio,
                ambito,
                escuela.Cueanexo,
                link=link,
                historia=historia,
            )
        popup_html = popup_html_cache[popup_cache_key]

        marcador = folium.Marker(
            location=[escuela.latitud, escuela.longitud],
            icon=folium.Icon(prefix="fa", color=color, icon="school"),
            tooltip=escuela.nombre,
            popup=_crear_popup_desde_html(popup_html),
            lazy=True,
        )
        marcador.add_to(capa)

        valores_busqueda = [
            str(valor).strip()
            for columna, valor in zip(escuelas.columns, escuela, strict=True)
            if columna not in columnas_no_indexadas
            and pd.notna(valor)
            and str(valor).strip()
        ]
        registros_busqueda.append(
            {
                "etiqueta": (
                    f"{escuela.nombre} — {escuela.Domicilio} · {nombre}"
                ),
                "texto": " ".join([nombre, *valores_busqueda]),
                "padron": nombre,
                "marcador": marcador.get_name(),
                "capa": capa.get_name(),
            }
        )

    return capa


def _crear_macro(nombre_plantilla: str, **contexto: object) -> branca.element.MacroElement:
    """Crea un macro Folium y le asigna el contexto de una plantilla.

    Precondiciones:
        ``nombre_plantilla`` identifica una plantilla legible incluida en el
        paquete y las claves de ``contexto`` son nombres de atributos validos.
    Postcondiciones:
        Retorna un nuevo ``MacroElement`` configurado con la plantilla y el
        contexto recibidos; no modifica los argumentos.
    """
    macro = branca.element.MacroElement()
    macro._template = branca.element.Template(cargar_plantilla(nombre_plantilla))
    for nombre, valor in contexto.items():
        setattr(macro, nombre, valor)
    return macro


def _agregar_selector_padrones(
    mapa: folium.Map,
    capas: dict[str, plugins.MarkerCluster],
    nombre_inicial: str,
    resumenes: dict[str, dict[str, int]],
) -> None:
    """Agrega al mapa el selector de padrón y su resumen por ámbito.

    Precondiciones:
        ``capas`` y ``resumenes`` contienen las mismas claves, no estan vacios,
        ``nombre_inicial`` pertenece a ambos y ``mapa`` es modificable.
    Postcondiciones:
        Agrega a ``mapa`` un macro con el selector y el resumen inicial;
        retorna ``None`` y no modifica las colecciones recibidas.
    """
    opciones_html = "\n".join(
        (
            f'<option value="{escape(nombre)}" '
            f'{"selected" if nombre == nombre_inicial else ""}>'
            f"{escape(nombre)}</option>"
        )
        for nombre in capas
    )
    capas_js = ",\n".join(
        f"{json.dumps(nombre)}: {capa.get_name()}"
        for nombre, capa in capas.items()
    )
    resumen_inicial = resumenes[nombre_inicial]
    macro = _crear_macro(
        "selector_padrones.js.jinja",
        map_name=mapa.get_name(),
        capas_js=capas_js,
        resumenes_js=json.dumps(resumenes, ensure_ascii=False),
        nombre_inicial_js=json.dumps(nombre_inicial),
        opciones_html=opciones_html,
        rurales=resumen_inicial["rurales"],
        urbanas=resumen_inicial["urbanas"],
    )
    mapa.add_child(macro)


def _agregar_estilos_selector_padrones(mapa: folium.Map) -> None:
    """Agrega al encabezado los estilos compartidos por los controles.

    Precondiciones:
        ``mapa`` posee un elemento raiz y la plantilla ``controles.css`` esta
        disponible en el paquete.
    Postcondiciones:
        Agrega una unica etiqueta ``style`` durante esta invocacion al
        encabezado de ``mapa`` y retorna ``None``.
    """
    css = cargar_plantilla("controles.css")
    mapa.get_root().header.add_child(folium.Element(f"<style>\n{css}\n</style>"))


def _agregar_buscador_escuelas(
    mapa: folium.Map,
    registros: list[dict[str, str]],
) -> None:
    """Agrega el buscador que activa capas y abre marcadores.

    Precondiciones:
        Cada elemento de ``registros`` contiene ``etiqueta``, ``texto``,
        ``padron``, ``marcador`` y ``capa``; ``mapa`` es modificable.
    Postcondiciones:
        Agrega a ``mapa`` un macro de busqueda construido con todos los
        registros, retorna ``None`` y no modifica la lista recibida.
    """
    registros_js = ",\n".join(
        "{" + ",".join(
            (
                f"etiqueta:{json.dumps(registro['etiqueta'])}",
                f"texto:{json.dumps(registro['texto'])}",
                f"padron:{json.dumps(registro['padron'])}",
                f"marcador:{registro['marcador']}",
                f"capa:{registro['capa']}",
            )
        ) + "}"
        for registro in reversed(registros)
    )
    macro = _crear_macro(
        "buscador_escuelas.js.jinja",
        map_name=mapa.get_name(),
        registros_js=registros_js,
    )
    mapa.add_child(macro)
