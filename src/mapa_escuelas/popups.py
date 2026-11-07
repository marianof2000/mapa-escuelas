# -*- coding: utf-8 -*-
"""Construcción del contenido de las fichas de las escuelas."""
from html import escape
from pathlib import Path
import branca
import folium
from .config import (
    IMAGENES_POPUP_PATH, IMAGEN_EXTENSION, IMAGEN_MUESTRA,
    IMAGEN_WEB_PATH, SPOTIFY_URL,
)
from .datos import _normalizar_cueanexo

def _separar_nombre(nombre_completo: str) -> tuple[str, str]:
    """Separa la denominacion de escuela de su nombre propio entre comillas.

    Precondiciones:
        ``nombre_completo`` es una cadena.
    Postcondiciones:
        Retorna una tupla de dos cadenas; la primera queda en formato titulo y
        la segunda es vacia o comienza en la primera comilla del texto original.
    """
    if '"' not in nombre_completo:
        return nombre_completo.title(), ""

    indice = nombre_completo.index('"')
    escuela = nombre_completo[:indice].strip().title()
    nombre = nombre_completo[indice:].strip()
    return escuela, nombre

def _ruta_imagen_popup(cueanexo: object) -> Path:
    """Construye la ruta local de la imagen asociada a una escuela.

    Precondiciones:
        ``cueanexo`` puede convertirse a texto.
    Postcondiciones:
        Retorna una ruta dentro de ``IMAGENES_POPUP_PATH`` con la extension
        configurada; no crea ni modifica el archivo.
    """
    cueanexo_limpio = _normalizar_cueanexo(cueanexo)
    return IMAGENES_POPUP_PATH / f"{cueanexo_limpio}{IMAGEN_EXTENSION}"

def _imagen_popup_src(cueanexo: object) -> str:
    """Obtiene la URL relativa de una imagen de popup existente.

    Precondiciones:
        ``cueanexo`` cumple el contrato de :func:`_ruta_imagen_popup`.
    Postcondiciones:
        Retorna la ruta web de la imagen propia de la escuela cuando existe o
        la miniatura de muestra configurada como respaldo.
    """
    ruta = _ruta_imagen_popup(cueanexo)
    if ruta.exists():
        return f"{IMAGEN_WEB_PATH}/{ruta.name}"

    ruta_muestra = IMAGENES_POPUP_PATH / IMAGEN_MUESTRA
    if not ruta_muestra.exists():
        return ""
    return f"{IMAGEN_WEB_PATH}/{ruta_muestra.name}"

def _crear_popup_html(
    nombre_completo: str,
    domicilio: str,
    ambito: str,
    cueanexo: object,
    link: str = "",
    historia: str = "Historia no disponible.",
) -> str:
    """Genera el HTML seguro del popup de una escuela.

    Precondiciones:
        ``nombre_completo``, ``domicilio`` y ``ambito`` son representables
        como texto, y ``cueanexo`` identifica la escuela.
    Postcondiciones:
        Retorna una cadena HTML con los datos escapados, el reproductor y, si
        existe, la imagen de la escuela; no modifica sus argumentos.
    """
    escuela, nombre = _separar_nombre(str(nombre_completo))
    imagen_src = _imagen_popup_src(cueanexo)
    imagen_alt = f"Imagen ilustrativa de {escuela}"
    historia_html = escape(historia).replace("\n", "<br>")
    link_html = ""
    if link:
        link_html = f"""
            <p class="popup-link">
                <a href="{escape(link)}" target="_blank" rel="noopener noreferrer">
                    Abrir enlace de la escuela
                </a>
            </p>
        """
    imagen_html = ""
    if imagen_src:
        imagen_html = f"""
        <figure class="popup-imagen">
            <img
                src="{escape(imagen_src)}"
                alt="{escape(imagen_alt)}"
                loading="lazy"
            >
        </figure>
        """
    return f"""
        <style>
            .popup-contenido {{
                width: 560px;
                max-width: calc(100vw - 80px);
            }}
            .popup-historia {{
                max-height: 180px;
                overflow-y: auto;
                margin: 0 0 12px;
                padding: 10px 12px;
                line-height: 1.4;
                background: #f5f7fa;
                border-left: 3px solid #1f4e78;
            }}
            .popup-historia p {{
                margin: 6px 0 0;
            }}
            .popup-link a {{
                display: inline-block;
                font-weight: 600;
            }}
            .popup-imagen {{
                width: 100%;
                height: 145px;
                margin: 0 0 14px;
                border-radius: 12px;
                overflow: hidden;
                background: #eef1f4;
                border: 1px solid #d8dde3;
            }}
            .popup-imagen img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }}
        </style>
        <div class="popup-contenido">
            <h4>
                {escape(escuela)} <br>
                {escape(nombre)}
            </h4>
            <p>
                <strong>Ubicación:</strong> {escape(str(domicilio))} <br>
                <strong>Ambito:</strong> {escape(str(ambito))} <br>
            </p>
            <div class="popup-historia">
                <strong>Historia:</strong>
                <p>{historia_html}</p>
            </div>
            {link_html}
            {imagen_html}
            <p>
                <iframe style="border-radius:12px"
                src="{SPOTIFY_URL}"
                width="100%" height="100" frameBorder="0"
                allowfullscreen="" allow="autoplay;
                clipboard-write; encrypted-media; fullscreen;
                picture-in-picture" loading="lazy">
                </iframe>
            </p>
        </div>
    """

def _crear_popup_desde_html(html: str) -> folium.Popup:
    """Construye un popup Folium a partir de contenido HTML.

    Precondiciones:
        ``html`` es una cadena con contenido apto para insertar en el mapa.
    Postcondiciones:
        Retorna un nuevo ``folium.Popup`` con ancho maximo de 600 pixeles; no
        modifica la cadena recibida.
    """
    return folium.Popup(branca.element.Html(html, script=True), max_width=600)
