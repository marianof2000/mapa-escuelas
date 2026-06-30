# -*- coding: utf-8 -*-
"""Genera el mapa interactivo de escuelas primarias de Dolores."""

import base64
from html import escape
import json
import mimetypes
from pathlib import Path

import branca
import folium
from folium import plugins
from folium.plugins import MiniMap, MousePosition
import pandas as pd


PADRON_PATH = Path("2023.09.04_padron_oficial_establecimientos_educativos_die.xlsx")
LIMITES_PATH = Path("limite_partidos.geojson")
OUTPUT_PATH = Path("maps-dol.html")
DESCRIPCIONES_PATH = Path("descripciones_escuelas.json")
IMAGENES_POPUP_PATH = Path("img")
IMAGEN_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

PRIMARIA_URL = (
    "https://github.com/marianof2000/datasets/raw/main/" "Nivel_Primario_G_Estatal.csv"
)
SPOTIFY_URL = (
    "https://open.spotify.com/embed/show/" "446QK5WSDCmetKGYV38zoi?utm_source=generator"
)


def cargar_limite_dolores() -> str:
    with LIMITES_PATH.open("rt", encoding="utf-8") as fh:
        partidos = json.load(fh)

    dolores = {key: partidos[key] for key in list(partidos.keys())[:3]}
    dolores["features"] = [
        feature
        for feature in partidos["features"]
        if "Dolores" in feature["properties"]["fna"]
    ]
    if not dolores["features"]:
        raise ValueError(
            "No se encontró el partido de Dolores en limite_partidos.geojson"
        )

    return json.dumps(dolores)


def cargar_escuelas() -> pd.DataFrame:
    padron = pd.read_excel(PADRON_PATH, sheet_name="padron", header=13)

    primaria = pd.read_csv(PRIMARIA_URL)
    primaria = primaria.rename(columns={"cueanexo": "Cueanexo"})
    columnas_primaria = (
        list(primaria.columns)[4:14]
        + list(primaria.columns)[17:19]
        + list(primaria.columns)[-5:-2]
    )
    primaria_dolores = primaria[columnas_primaria]
    primaria_dolores = primaria_dolores[primaria_dolores["localidad"] == "DOLORES"]

    padron_dolores = padron[
        (padron["Jurisdicción"] == "Buenos Aires")
        & (padron["Primario"].notna())
        & (padron["Localidad"] == "DOLORES")
    ].loc[:, :"Mail"]

    escuelas = pd.merge(
        primaria_dolores,
        padron_dolores,
        how="left",
        on="Cueanexo",
        validate="one_to_one",
    )
    return escuelas.dropna(subset=["latitud", "longitud"])


def cargar_descripciones() -> dict[str, str]:
    if not DESCRIPCIONES_PATH.exists():
        return {}

    with DESCRIPCIONES_PATH.open("rt", encoding="utf-8") as fh:
        descripciones = json.load(fh)

    return {
        str(cueanexo): str(descripcion)
        for cueanexo, descripcion in descripciones.items()
    }


def separar_nombre(nombre_completo: str) -> tuple[str, str]:
    if '"' not in nombre_completo:
        return nombre_completo.title(), ""

    indice = nombre_completo.index('"')
    escuela = nombre_completo[:indice].strip().title()
    nombre = nombre_completo[indice:].strip()
    return escuela, nombre


def ruta_imagen_popup(cueanexo: object) -> Path:
    cueanexo_limpio = str(cueanexo).strip()
    for extension in IMAGEN_EXTENSIONS:
        ruta = IMAGENES_POPUP_PATH / f"{cueanexo_limpio}{extension}"
        if ruta.exists():
            return ruta

    return IMAGENES_POPUP_PATH / f"{cueanexo_limpio}.jpg"


def imagen_popup_src(cueanexo: object) -> str:
    ruta = ruta_imagen_popup(cueanexo)
    if not ruta.exists():
        return ""

    mime_type = mimetypes.guess_type(ruta)[0] or "image/jpeg"
    imagen_base64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{imagen_base64}"


def crear_popup(
    nombre_completo: str,
    domicilio: str,
    ambito: str,
    cueanexo: object,
    descripcion: str,
) -> folium.Popup:
    escuela, nombre = separar_nombre(str(nombre_completo))
    imagen_src = imagen_popup_src(cueanexo)
    imagen_alt = f"Imagen ilustrativa de {escuela}"
    descripcion_html = escape(descripcion).replace("\n", "<br>")
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
    html = f"""
        <style>
            .popup-descripcion {{
                margin: 0 0 12px;
                line-height: 1.35;
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
        <h4>
            {escape(escuela)} <br>
            {escape(nombre)}
        </h4>
        <p>
            <strong>Ubicación:</strong> {escape(str(domicilio))} <br>
            <strong>Ambito:</strong> {escape(str(ambito))} <br>
        </p>
        <p class="popup-descripcion">
            {descripcion_html}
        </p>
        {imagen_html}
        <p>
            <iframe style="border-radius:12px"
            src="{SPOTIFY_URL}"
            width="90%" height="100" frameBorder="0"
            allowfullscreen="" allow="autoplay;
            clipboard-write; encrypted-media; fullscreen;
            picture-in-picture" loading="lazy">
            </iframe>
        </p>
    """
    iframe = branca.element.IFrame(html=html, width=400, height=420)
    return folium.Popup(iframe, max_width=500)


def crear_mapa(
    escuelas: pd.DataFrame,
    limite_dolores: str,
    descripciones: dict[str, str],
) -> folium.Map:
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

    escuelas_agrupadas = plugins.MarkerCluster().add_to(mapa)
    for escuela in escuelas.itertuples(index=False):
        ambito = getattr(escuela, "Ámbito")
        color = "orange" if ambito == "Rural" else "lightblue"
        cueanexo = str(escuela.Cueanexo).strip()
        descripcion = descripciones.get(cueanexo, "Descripción pendiente.")

        folium.Marker(
            location=[escuela.latitud, escuela.longitud],
            icon=folium.Icon(prefix="fa", color=color, icon="school"),
            tooltip=escuela.nombre,
            popup=crear_popup(
                escuela.nombre,
                escuela.Domicilio,
                ambito,
                escuela.Cueanexo,
                descripcion,
            ),
            lazy=True,
        ).add_to(escuelas_agrupadas)

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


def main() -> None:
    limite_dolores = cargar_limite_dolores()
    escuelas = cargar_escuelas()
    descripciones = cargar_descripciones()
    mapa = crear_mapa(escuelas, limite_dolores, descripciones)
    mapa.save(OUTPUT_PATH)
    print(f"Mapa generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
