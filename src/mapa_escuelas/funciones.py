# -*- coding: utf-8 -*-
"""Funciones para generar el mapa interactivo de escuelas de Dolores."""

from html import escape
import json
import logging
from pathlib import Path
import re

import branca
import folium
from folium import plugins
from folium.plugins import MiniMap, MousePosition
import pandas as pd

from .config import (
    DESCRIPCIONES_PATH,
    IMAGENES_POPUP_PATH,
    IMAGEN_EXTENSION,
    IMAGEN_WEB_PATH,
    LIMITES_PATH,
    PADRONES_CSV_PATH,
    PADRONES_DIR,
    PADRON_COLUMNAS_REQUERIDAS,
    PADRON_FILAS_DE_BUSQUEDA,
    PADRON_PATH,
    PRIMARIA_COLUMNAS,
    PRIMARIA_URL,
    SPOTIFY_URL,
)


LOGGER = logging.getLogger(__name__)


def cargar_limite_dolores(path: Path = LIMITES_PATH) -> str:
    with path.open("rt", encoding="utf-8") as fh:
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


def _detectar_hoja_y_header_padron(path: Path) -> tuple[str, int]:
    with pd.ExcelFile(path) as excel:
        hojas = sorted(
            excel.sheet_names,
            key=lambda hoja: 0 if hoja.casefold() == "padron" else 1,
        )

    for hoja in hojas:
        preview = pd.read_excel(
            path,
            sheet_name=hoja,
            header=None,
            nrows=PADRON_FILAS_DE_BUSQUEDA,
        )
        for indice, fila in preview.iterrows():
            valores = {str(valor).strip() for valor in fila.dropna()}
            if PADRON_COLUMNAS_REQUERIDAS.issubset(valores):
                return hoja, int(indice)

    columnas = ", ".join(sorted(PADRON_COLUMNAS_REQUERIDAS))
    raise ValueError(
        f"No se encontro el encabezado del padron en {path}. "
        f"Columnas requeridas: {columnas}"
    )


def _cargar_padron(path: Path) -> pd.DataFrame:
    hoja, header = _detectar_hoja_y_header_padron(path)
    padron = pd.read_excel(path, sheet_name=hoja, header=header)
    padron.columns = [str(columna).strip() for columna in padron.columns]
    return padron


def listar_padrones(path: Path = PADRONES_DIR) -> list[Path]:
    return sorted(path.glob("*.xlsx"))


def _nombre_padron(path: Path) -> str:
    coincidencia = re.search(r"(20\d{2})(?:[._-](\d{2}))?", path.stem)
    if coincidencia and coincidencia.group(2):
        return f"{coincidencia.group(1)}.{coincidencia.group(2)}"
    if coincidencia:
        return coincidencia.group(1)

    return path.stem.replace("_", " ")


def _cargar_primaria(primaria_url: str = PRIMARIA_URL) -> pd.DataFrame:
    primaria = pd.read_csv(primaria_url)
    columnas_faltantes = sorted(set(PRIMARIA_COLUMNAS) - set(primaria.columns))
    if columnas_faltantes:
        faltantes = ", ".join(columnas_faltantes)
        raise ValueError(f"Faltan columnas en el CSV de primaria: {faltantes}")

    primaria_dolores = primaria.loc[:, PRIMARIA_COLUMNAS].copy()
    primaria_dolores = primaria_dolores.rename(columns={"cueanexo": "Cueanexo"})
    return primaria_dolores[primaria_dolores["localidad"] == "DOLORES"]


def _combinar_padron_con_primaria(
    padron_path: Path,
    primaria_dolores: pd.DataFrame,
) -> pd.DataFrame:
    padron = _cargar_padron(padron_path)

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


def cargar_escuelas(
    padron_path: Path = PADRON_PATH,
    primaria_url: str = PRIMARIA_URL,
) -> pd.DataFrame:
    primaria_dolores = _cargar_primaria(primaria_url)
    return _combinar_padron_con_primaria(padron_path, primaria_dolores)


def cargar_escuelas_por_padron(
    padrones: list[Path] | None = None,
    primaria_url: str = PRIMARIA_URL,
) -> dict[str, pd.DataFrame]:
    padrones = padrones if padrones is not None else listar_padrones()
    primaria_dolores = _cargar_primaria(primaria_url)
    escuelas_por_padron = {}

    for padron_path in padrones:
        try:
            escuelas = _combinar_padron_con_primaria(padron_path, primaria_dolores)
        except (KeyError, ValueError) as exc:
            LOGGER.warning("Se omite %s: %s", padron_path, exc)
            continue
        if not escuelas.empty:
            escuelas_por_padron[_nombre_padron(padron_path)] = escuelas

    if not escuelas_por_padron:
        raise ValueError("No se encontraron padrones validos para crear capas")

    return escuelas_por_padron


def cargar_escuelas_por_padron_csv(
    path: Path = PADRONES_CSV_PATH,
) -> dict[str, pd.DataFrame]:
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path}. Ejecuta `python3 convertir.py` primero."
        )

    padrones = pd.read_csv(path)
    columnas_requeridas = {
        "padron",
        "padron_nombre",
        "Cueanexo",
        "nombre",
        "latitud",
        "longitud",
        "Domicilio",
        "Ámbito",
    }
    columnas_faltantes = sorted(columnas_requeridas - set(padrones.columns))
    if columnas_faltantes:
        faltantes = ", ".join(columnas_faltantes)
        raise ValueError(f"Faltan columnas en {path}: {faltantes}")

    padrones = padrones.dropna(subset=["latitud", "longitud"])
    escuelas_por_padron = {}
    for padron, escuelas in padrones.groupby("padron_nombre", sort=False):
        escuelas_por_padron[str(padron)] = escuelas.copy()

    if not escuelas_por_padron:
        raise ValueError(f"No hay escuelas con coordenadas en {path}")

    return escuelas_por_padron


def cargar_descripciones(path: Path = DESCRIPCIONES_PATH) -> dict[str, str]:
    if not path.exists():
        return {}

    with path.open("rt", encoding="utf-8") as fh:
        descripciones = json.load(fh)

    return {
        str(cueanexo): str(descripcion)
        for cueanexo, descripcion in descripciones.items()
    }


def _separar_nombre(nombre_completo: str) -> tuple[str, str]:
    if '"' not in nombre_completo:
        return nombre_completo.title(), ""

    indice = nombre_completo.index('"')
    escuela = nombre_completo[:indice].strip().title()
    nombre = nombre_completo[indice:].strip()
    return escuela, nombre


def _ruta_imagen_popup(cueanexo: object) -> Path:
    cueanexo_limpio = str(cueanexo).strip()
    return IMAGENES_POPUP_PATH / f"{cueanexo_limpio}{IMAGEN_EXTENSION}"


def _imagen_popup_src(cueanexo: object) -> str:
    ruta = _ruta_imagen_popup(cueanexo)
    if not ruta.exists():
        return ""

    return f"{IMAGEN_WEB_PATH}/{ruta.name}"


def _crear_popup_html(
    nombre_completo: str,
    domicilio: str,
    ambito: str,
    cueanexo: object,
    descripcion: str,
) -> str:
    escuela, nombre = _separar_nombre(str(nombre_completo))
    imagen_src = _imagen_popup_src(cueanexo)
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
    return f"""
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


def _crear_popup_desde_html(html: str) -> folium.Popup:
    return folium.Popup(branca.element.Html(html, script=True), max_width=420)


def _crear_capa_escuelas(
    escuelas: pd.DataFrame,
    descripciones: dict[str, str],
    nombre: str,
    popup_html_cache: dict[tuple[str, str, str, str], str],
) -> plugins.MarkerCluster:
    capa = plugins.MarkerCluster(name=nombre, control=False)
    for escuela in escuelas.itertuples(index=False):
        ambito = getattr(escuela, "Ámbito")
        color = "orange" if ambito == "Rural" else "lightblue"
        cueanexo = str(escuela.Cueanexo).strip()
        descripcion = descripciones.get(cueanexo, "Descripción pendiente.")
        popup_cache_key = (cueanexo, str(escuela.Domicilio), str(ambito), descripcion)
        if popup_cache_key not in popup_html_cache:
            popup_html_cache[popup_cache_key] = _crear_popup_html(
                escuela.nombre,
                escuela.Domicilio,
                ambito,
                escuela.Cueanexo,
                descripcion,
            )
        popup_html = popup_html_cache[popup_cache_key]

        folium.Marker(
            location=[escuela.latitud, escuela.longitud],
            icon=folium.Icon(prefix="fa", color=color, icon="school"),
            tooltip=escuela.nombre,
            popup=_crear_popup_desde_html(popup_html),
            lazy=True,
        ).add_to(capa)

    return capa


def _agregar_selector_padrones(
    mapa: folium.Map,
    capas: dict[str, plugins.MarkerCluster],
    nombre_inicial: str,
) -> None:
    opciones = "\n".join(
        f"""
        <label>
            <input
                type="radio"
                name="padron-selector"
                value="{escape(nombre)}"
                {"checked" if nombre == nombre_inicial else ""}
            >
            {escape(nombre)}
        </label>
        """
        for nombre in capas
    )
    capas_js = ",\n".join(
        f"{json.dumps(nombre)}: {capa.get_name()}" for nombre, capa in capas.items()
    )
    nombre_inicial_js = json.dumps(nombre_inicial)

    template = branca.element.Template(
        f"""
        {{% macro script(this, kwargs) %}}
        (function() {{
            var map = {mapa.get_name()};
            var capasPadron = {{
                {capas_js}
            }};
            var capaActiva = {nombre_inicial_js};

            Object.keys(capasPadron).forEach(function(nombre) {{
                if (nombre !== capaActiva && map.hasLayer(capasPadron[nombre])) {{
                    map.removeLayer(capasPadron[nombre]);
                }}
            }});

            var control = L.control({{position: "topright"}});
            control.onAdd = function() {{
                var div = L.DomUtil.create("div", "padron-selector-control");
                div.innerHTML = `
                    <strong>Padrón</strong>
                    <div class="padron-selector-opciones">
                        {opciones}
                    </div>
                `;
                L.DomEvent.disableClickPropagation(div);
                L.DomEvent.disableScrollPropagation(div);
                return div;
            }};
            control.addTo(map);

            document
                .querySelectorAll(".padron-selector-control input")
                .forEach(function(input) {{
                    input.addEventListener("change", function(event) {{
                        Object.keys(capasPadron).forEach(function(nombre) {{
                            if (map.hasLayer(capasPadron[nombre])) {{
                                map.removeLayer(capasPadron[nombre]);
                            }}
                        }});
                        capaActiva = event.target.value;
                        map.addLayer(capasPadron[capaActiva]);
                    }});
                }});
        }})();
        {{% endmacro %}}
        """
    )
    macro = branca.element.MacroElement()
    macro._template = template
    mapa.add_child(macro)


def _agregar_estilos_selector_padrones(mapa: folium.Map) -> None:
    css = """
        <style>
            .padron-selector-control {
                max-width: 280px;
                padding: 10px 12px;
                background: rgba(255, 255, 255, 0.95);
                border: 2px solid rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                box-shadow: 0 1px 5px rgba(0, 0, 0, 0.35);
                font: 13px/1.3 Arial, sans-serif;
            }
            .padron-selector-control strong {
                display: block;
                margin-bottom: 8px;
            }
            .padron-selector-control label {
                display: block;
                margin: 0 0 6px;
                cursor: pointer;
            }
            .padron-selector-control input {
                margin: 0 6px 0 0;
                vertical-align: middle;
            }
        </style>
    """
    mapa.get_root().header.add_child(folium.Element(css))


def crear_mapa(
    escuelas_por_padron: dict[str, pd.DataFrame] | pd.DataFrame,
    limite_dolores: str,
    descripciones: dict[str, str],
) -> folium.Map:
    if isinstance(escuelas_por_padron, pd.DataFrame):
        escuelas_por_padron = {_nombre_padron(PADRON_PATH): escuelas_por_padron}

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
    popup_html_cache = {}
    for nombre, escuelas in escuelas_por_padron.items():
        capa = _crear_capa_escuelas(escuelas, descripciones, nombre, popup_html_cache)
        capa.add_to(mapa)
        capas[nombre] = capa

    if capas:
        nombre_inicial = next(reversed(capas))
        _agregar_estilos_selector_padrones(mapa)
        _agregar_selector_padrones(mapa, capas, nombre_inicial)

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
