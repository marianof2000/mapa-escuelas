# -*- coding: utf-8 -*-
"""Funciones para generar el mapa interactivo de escuelas de Dolores."""

from decimal import Decimal, InvalidOperation
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
    IMAGEN_MUESTRA,
    IMAGEN_WEB_PATH,
    HISTORIAS_PATH,
    LINKS_PATH,
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
PADRON_EXCEL_ENGINE = "calamine"


def cargar_limite_dolores(path: Path = LIMITES_PATH) -> str:
    """Carga y serializa el limite geografico del partido de Dolores.

    Precondiciones:
        ``path`` referencia un GeoJSON legible con una lista ``features`` cuyos
        elementos poseen ``properties.fna``.
    Postcondiciones:
        Retorna un JSON en texto que conserva solo las features de Dolores y
        contiene al menos una; no modifica el archivo de origen.
    """
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


def _detectar_hoja_y_header_en_excel(
    excel: pd.ExcelFile,
    path: Path,
) -> tuple[str, int]:
    """Localiza la hoja y la fila de encabezado en un libro ya abierto."""
    hojas = sorted(
        excel.sheet_names,
        key=lambda hoja: 0 if hoja.casefold() == "padron" else 1,
    )

    for hoja in hojas:
        preview = pd.read_excel(
            excel,
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


def _detectar_hoja_y_header_padron(path: Path) -> tuple[str, int]:
    """Localiza con Calamine la hoja y la fila de encabezado de un padron XLSX.

    Precondiciones:
        ``path`` referencia un libro de Excel legible y sus primeras filas
        contienen, en alguna hoja, las columnas requeridas del padron.
    Postcondiciones:
        Retorna el nombre de la hoja y un indice de fila no negativo; si no se
        encuentra el encabezado, lanza ``ValueError``.
    """
    with pd.ExcelFile(path, engine=PADRON_EXCEL_ENGINE) as excel:
        return _detectar_hoja_y_header_en_excel(excel, path)


def _cargar_padron(path: Path) -> pd.DataFrame:
    """Carga un padron y normaliza los nombres de sus columnas.

    Precondiciones:
        ``path`` cumple el formato requerido por
        :func:`_detectar_hoja_y_header_padron`.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` cuyas etiquetas de columna son cadenas
        sin espacios exteriores; no modifica el libro de origen.
    """
    with pd.ExcelFile(path, engine=PADRON_EXCEL_ENGINE) as excel:
        hoja, header = _detectar_hoja_y_header_en_excel(excel, path)
        padron = pd.read_excel(excel, sheet_name=hoja, header=header)
    padron.columns = [str(columna).strip() for columna in padron.columns]
    return padron


def listar_padrones(path: Path = PADRONES_DIR) -> list[Path]:
    """Lista los libros XLSX disponibles en un directorio.

    Precondiciones:
        ``path`` es una ruta valida de directorio o una ruta inexistente.
    Postcondiciones:
        Retorna una lista ordenada de rutas hijas con extension ``.xlsx``; la
        lista es vacia cuando no hay coincidencias.
    """
    return sorted(path.glob("*.xlsx"))


def _nombre_padron(path: Path) -> str:
    """Obtiene una etiqueta legible a partir del nombre de un padron.

    Precondiciones:
        ``path`` posee un nombre de archivo representable como texto.
    Postcondiciones:
        Retorna ``AAAA.MM`` o ``AAAA`` si detecta una fecha; en otro caso,
        retorna el nombre base reemplazando guiones bajos por espacios.
    """
    coincidencia = re.search(r"(20\d{2})(?:[._-](\d{2}))?", path.stem)
    if coincidencia and coincidencia.group(2):
        return f"{coincidencia.group(1)}.{coincidencia.group(2)}"
    if coincidencia:
        return coincidencia.group(1)

    return path.stem.replace("_", " ")


def _etiqueta_padron(nombre: str) -> str:
    """Devuelve la etiqueta visible correspondiente a un padron."""
    if nombre in {"2010", "Padrón 2010"}:
        return "Anterior a 2011"
    return nombre


def _anio_para_ordenar_padron(nombre: str) -> int:
    """Obtiene el anio usado para ordenar las etiquetas de padrones."""
    if nombre == "Anterior a 2011":
        return 2010
    coincidencia = re.search(r"20\d{2}", nombre)
    return int(coincidencia.group()) if coincidencia else -1


def _normalizar_cueanexo(valor: object) -> str:
    """Normaliza un Cueanexo para usarlo como clave entre archivos CSV."""
    texto = str(valor).strip().replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return texto
    if numero == numero.to_integral_value():
        return format(numero.quantize(Decimal("1")), "f")
    return format(numero.normalize(), "f")


def _cargar_primaria(primaria_url: str = PRIMARIA_URL) -> pd.DataFrame:
    """Carga las escuelas primarias estatales desde un CSV.

    Precondiciones:
        ``primaria_url`` identifica un CSV accesible con las columnas definidas
        en ``PRIMARIA_COLUMNAS``.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` con las columnas esperadas y
        ``cueanexo`` renombrada como ``Cueanexo``; lanza ``ValueError`` si
        falta alguna columna. La selección territorial queda a cargo del
        padrón oficial.
    """
    primaria = pd.read_csv(primaria_url)
    columnas_faltantes = sorted(set(PRIMARIA_COLUMNAS) - set(primaria.columns))
    if columnas_faltantes:
        faltantes = ", ".join(columnas_faltantes)
        raise ValueError(f"Faltan columnas en el CSV de primaria: {faltantes}")

    primaria = primaria.loc[:, PRIMARIA_COLUMNAS].copy()
    return primaria.rename(columns={"cueanexo": "Cueanexo"})


def _combinar_padron_con_primaria(
    padron_path: Path,
    primaria: pd.DataFrame,
    conservar_sin_coordenadas: bool = False,
) -> pd.DataFrame:
    """Combina un padron oficial con las coordenadas de escuelas primarias.

    Precondiciones:
        ``padron_path`` contiene las columnas oficiales requeridas y
        ``primaria`` posee ``Cueanexo``, coordenadas y datos de escuela con
        claves unicas compatibles con una union uno a uno.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` con las escuelas primarias estatales del
        partido de Dolores. Conserva las que no tienen coordenadas solo cuando
        ``conservar_sin_coordenadas`` es verdadero; no modifica ``primaria``.
    """
    padron = _cargar_padron(padron_path)
    primario_activo = pd.to_numeric(padron["Primario"], errors="coerce").eq(1)

    padron_dolores = padron[
        (padron["Jurisdicción"] == "Buenos Aires")
        & (padron["Sector"] == "Estatal")
        & primario_activo
        & (padron["Departamento"].astype(str).str.strip().str.casefold() == "dolores")
    ].loc[:, :"Mail"]

    escuelas = pd.merge(
        padron_dolores,
        primaria,
        how="left",
        on="Cueanexo",
        validate="one_to_one",
    )
    if conservar_sin_coordenadas:
        return escuelas

    return escuelas.dropna(subset=["latitud", "longitud"])


def cargar_escuelas(
    padron_path: Path = PADRON_PATH,
    primaria_url: str = PRIMARIA_URL,
) -> pd.DataFrame:
    """Carga las escuelas de Dolores correspondientes a un unico padron.

    Precondiciones:
        ``padron_path`` y ``primaria_url`` cumplen los contratos de
        :func:`_combinar_padron_con_primaria` y :func:`_cargar_primaria`.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` de escuelas con coordenadas validas; no
        modifica las fuentes de datos.
    """
    primaria = _cargar_primaria(primaria_url)
    return _combinar_padron_con_primaria(padron_path, primaria)


def cargar_escuelas_por_padron(
    padrones: list[Path] | None = None,
    primaria_url: str = PRIMARIA_URL,
) -> dict[str, pd.DataFrame]:
    """Carga y agrupa las escuelas validas de uno o mas padrones.

    Precondiciones:
        ``primaria_url`` cumple el contrato de :func:`_cargar_primaria` y cada
        elemento de ``padrones``, si se informa, es una ruta de padron.
    Postcondiciones:
        Retorna un diccionario no vacio de nombres a ``DataFrame`` no vacios;
        omite padrones incompatibles y lanza ``ValueError`` si ninguno sirve.
    """
    padrones = padrones if padrones is not None else listar_padrones()
    primaria = _cargar_primaria(primaria_url)
    escuelas_por_padron = {}

    for padron_path in padrones:
        try:
            escuelas = _combinar_padron_con_primaria(padron_path, primaria)
        except (KeyError, ValueError) as exc:
            LOGGER.warning("Se omite %s: %s", padron_path, exc)
            continue
        if not escuelas.empty:
            nombre = _etiqueta_padron(_nombre_padron(padron_path))
            escuelas_por_padron[nombre] = escuelas

    if not escuelas_por_padron:
        raise ValueError("No se encontraron padrones validos para crear capas")

    return escuelas_por_padron


def cargar_escuelas_por_padron_csv(
    path: Path = PADRONES_CSV_PATH,
    links_path: Path = LINKS_PATH,
    historias_path: Path = HISTORIAS_PATH,
) -> dict[str, pd.DataFrame]:
    """Carga desde CSV las escuelas agrupadas por nombre de padron.

    Precondiciones:
        ``path`` referencia un CSV legible con todas las columnas requeridas.
    Postcondiciones:
        Retorna un diccionario no vacio cuyos valores son copias de grupos con
        coordenadas presentes; lanza ``FileNotFoundError`` si no existe la
        fuente y ``ValueError`` si su estructura o contenido no es valido.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path}. Ejecuta `python3 convertir.py` primero."
        )
    if not links_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de enlaces {links_path}")
    if not historias_path.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo de historias {historias_path}"
        )

    padrones = pd.read_csv(path)
    links = pd.read_csv(links_path, dtype=str)
    historias = pd.read_csv(historias_path, dtype=str, encoding="utf-8-sig")
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

    columnas_links = {"padron", "Cueanexo", "link"}
    links_faltantes = sorted(columnas_links - set(links.columns))
    if links_faltantes:
        faltantes = ", ".join(links_faltantes)
        raise ValueError(f"Faltan columnas en {links_path}: {faltantes}")

    columnas_historias = {"Cueanexo", "historia"}
    historias_faltantes = sorted(columnas_historias - set(historias.columns))
    if historias_faltantes:
        faltantes = ", ".join(historias_faltantes)
        raise ValueError(f"Faltan columnas en {historias_path}: {faltantes}")

    padrones = padrones.copy()
    links = links.copy()
    padrones["_cue_link"] = padrones["Cueanexo"].map(_normalizar_cueanexo)
    links["_cue_link"] = links["Cueanexo"].map(_normalizar_cueanexo)
    if links.duplicated(subset=["padron", "_cue_link"]).any():
        raise ValueError(f"Hay enlaces duplicados en {links_path}")

    padrones = pd.merge(
        padrones,
        links.loc[:, ["padron", "_cue_link", "link"]],
        how="left",
        on=["padron", "_cue_link"],
        validate="one_to_one",
    ).drop(columns="_cue_link")
    sin_link = padrones["link"].isna() | padrones["link"].str.strip().eq("")
    if sin_link.any():
        cantidad = int(sin_link.sum())
        raise ValueError(f"Faltan enlaces para {cantidad} marcadores en {links_path}")

    historias = historias.copy()
    historias["_cue_historia"] = historias["Cueanexo"].fillna("").map(
        _normalizar_cueanexo
    )
    historias = historias[historias["_cue_historia"].ne("")]
    if historias.duplicated(subset="_cue_historia").any():
        raise ValueError(f"Hay historias duplicadas por CUE en {historias_path}")

    padrones["_cue_historia"] = padrones["Cueanexo"].map(_normalizar_cueanexo)
    padrones = pd.merge(
        padrones,
        historias.loc[:, ["_cue_historia", "historia"]],
        how="left",
        on="_cue_historia",
        validate="many_to_one",
    ).drop(columns="_cue_historia")
    padrones["historia"] = padrones["historia"].fillna(
        "Historia no disponible."
    )
    padrones.loc[padrones["historia"].str.strip().eq(""), "historia"] = (
        "Historia no disponible."
    )

    padrones = padrones.dropna(subset=["latitud", "longitud"])
    escuelas_por_padron = {}
    for padron, escuelas in padrones.groupby("padron_nombre", sort=False):
        escuelas_por_padron[_etiqueta_padron(str(padron))] = escuelas.copy()

    if not escuelas_por_padron:
        raise ValueError(f"No hay escuelas con coordenadas en {path}")

    return escuelas_por_padron


def cargar_descripciones(path: Path = DESCRIPCIONES_PATH) -> dict[str, str]:
    """Carga las descripciones de escuelas desde un objeto JSON.

    Precondiciones:
        Si ``path`` existe, es un JSON legible cuyo nivel superior es un objeto.
    Postcondiciones:
        Retorna un nuevo diccionario con claves y valores convertidos a texto;
        retorna un diccionario vacio si el archivo no existe.
    """
    if not path.exists():
        return {}

    with path.open("rt", encoding="utf-8") as fh:
        descripciones = json.load(fh)

    return {
        str(cueanexo): str(descripcion)
        for cueanexo, descripcion in descripciones.items()
    }


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
    descripcion: str,
    link: str = "",
    historia: str = "Historia no disponible.",
) -> str:
    """Genera el HTML seguro del popup de una escuela.

    Precondiciones:
        ``nombre_completo``, ``domicilio``, ``ambito`` y ``descripcion`` son
        representables como texto, y ``cueanexo`` identifica la escuela.
    Postcondiciones:
        Retorna una cadena HTML con los datos escapados, el reproductor y, si
        existe, la imagen de la escuela; no modifica sus argumentos.
    """
    escuela, nombre = _separar_nombre(str(nombre_completo))
    imagen_src = _imagen_popup_src(cueanexo)
    imagen_alt = f"Imagen ilustrativa de {escuela}"
    descripcion_html = escape(descripcion).replace("\n", "<br>")
    descripcion_bloque = ""
    if descripcion_html:
        descripcion_bloque = f"""
            <p class="popup-descripcion">
                {descripcion_html}
            </p>
        """
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
            .popup-descripcion {{
                margin: 0 0 12px;
                line-height: 1.35;
            }}
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
            {descripcion_bloque}
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


def _crear_capa_escuelas(
    escuelas: pd.DataFrame,
    descripciones: dict[str, str],
    nombre: str,
    popup_html_cache: dict[tuple[str, str, str, str, str, str], str],
    registros_busqueda: list[dict[str, str]],
) -> plugins.MarkerCluster:
    """Crea una capa de marcadores para un conjunto de escuelas.

    Precondiciones:
        ``escuelas`` contiene nombre, Cueanexo, Domicilio, Ambito, latitud y
        longitud; ``descripciones`` y ``popup_html_cache`` son diccionarios,
        ``registros_busqueda`` es una lista mutable y ``nombre`` identifica la
        capa.
    Postcondiciones:
        Retorna un nuevo ``MarkerCluster`` con un marcador por fila y agrega al
        cache el HTML faltante y un registro de busqueda por marcador, sin
        modificar ``escuelas`` ni ``descripciones``.
    """
    capa = plugins.MarkerCluster(name=nombre, control=False)
    for escuela in escuelas.itertuples(index=False):
        ambito = getattr(escuela, "Ámbito")
        color = "orange" if ambito == "Rural" else "lightblue"
        cueanexo = _normalizar_cueanexo(escuela.Cueanexo)
        descripcion = descripciones.get(cueanexo, "").strip()
        link = str(getattr(escuela, "link", "")).strip()
        historia = str(
            getattr(escuela, "historia", "Historia no disponible.")
        ).strip() or "Historia no disponible."
        popup_cache_key = (
            cueanexo,
            str(escuela.Domicilio),
            str(ambito),
            descripcion,
            link,
            historia,
        )
        if popup_cache_key not in popup_html_cache:
            popup_html_cache[popup_cache_key] = _crear_popup_html(
                escuela.nombre,
                escuela.Domicilio,
                ambito,
                escuela.Cueanexo,
                descripcion,
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
            for valor in escuela
            if pd.notna(valor) and str(valor).strip()
        ]
        registros_busqueda.append(
            {
                "etiqueta": (
                    f"{escuela.nombre} — {escuela.Domicilio} · {nombre}"
                ),
                "texto": " ".join([nombre, descripcion, *valores_busqueda]),
                "padron": nombre,
                "marcador": marcador.get_name(),
                "capa": capa.get_name(),
            }
        )

    return capa


def _agregar_selector_padrones(
    mapa: folium.Map,
    capas: dict[str, plugins.MarkerCluster],
    nombre_inicial: str,
    resumenes: dict[str, dict[str, int]],
) -> None:
    """Agrega al mapa un selector excluyente de capas de padrones.

    Precondiciones:
        ``mapa`` es un mapa Folium, ``capas`` no es vacio y contiene
        ``nombre_inicial``; cada valor es una capa ya vinculable al mapa.
    Postcondiciones:
        Agrega un macro de control al mapa y retorna ``None``; no modifica el
        diccionario ``capas``.
    """
    opciones = "\n".join(
        f"""
        <option
            value="{escape(nombre)}"
            {"selected" if nombre == nombre_inicial else ""}
        >{escape(nombre)}</option>
        """
        for nombre in capas
    )
    capas_js = ",\n".join(
        f"{json.dumps(nombre)}: {capa.get_name()}" for nombre, capa in capas.items()
    )
    nombre_inicial_js = json.dumps(nombre_inicial)
    resumenes_js = json.dumps(resumenes, ensure_ascii=False)
    resumen_inicial = resumenes[nombre_inicial]

    template = branca.element.Template(
        f"""
        {{% macro script(this, kwargs) %}}
        (function() {{
            var map = {mapa.get_name()};
            var capasPadron = {{
                {capas_js}
            }};
            var resumenesPadron = {resumenes_js};
            var capaActiva = {nombre_inicial_js};

            function actualizarResumen(nombre) {{
                var resumen = resumenesPadron[nombre];
                var rurales = document.querySelector(
                    ".padron-resumen-rurales strong"
                );
                var urbanas = document.querySelector(
                    ".padron-resumen-urbanas strong"
                );
                if (resumen && rurales && urbanas) {{
                    rurales.textContent = resumen.rurales;
                    urbanas.textContent = resumen.urbanas;
                }}
            }}

            Object.keys(capasPadron).forEach(function(nombre) {{
                if (nombre !== capaActiva && map.hasLayer(capasPadron[nombre])) {{
                    map.removeLayer(capasPadron[nombre]);
                }}
            }});

            var control = L.control({{position: "topright"}});
            control.onAdd = function() {{
                var div = L.DomUtil.create("div", "padron-selector-control");
                div.innerHTML = `
                    <label for="padron-selector-lista">Padrón</label>
                    <select
                        id="padron-selector-lista"
                        name="padron-selector"
                    >
                        {opciones}
                    </select>
                    <div class="padron-resumen" aria-live="polite">
                        <span class="padron-resumen-rurales">
                            Rurales: <strong>{resumen_inicial['rurales']}</strong>
                        </span>
                        <span class="padron-resumen-urbanas">
                            Urbanas: <strong>{resumen_inicial['urbanas']}</strong>
                        </span>
                    </div>
                `;
                L.DomEvent.disableClickPropagation(div);
                L.DomEvent.disableScrollPropagation(div);
                return div;
            }};
            control.addTo(map);

            document
                .querySelector(".padron-selector-control select")
                .addEventListener("change", function(event) {{
                    Object.keys(capasPadron).forEach(function(nombre) {{
                        if (map.hasLayer(capasPadron[nombre])) {{
                            map.removeLayer(capasPadron[nombre]);
                        }}
                    }});
                    capaActiva = event.target.value;
                    map.addLayer(capasPadron[capaActiva]);
                    actualizarResumen(capaActiva);
                }});
        }})();
        {{% endmacro %}}
        """
    )
    macro = branca.element.MacroElement()
    macro._template = template
    mapa.add_child(macro)


def _agregar_estilos_selector_padrones(mapa: folium.Map) -> None:
    """Agrega al encabezado del mapa los estilos CSS del selector.

    Precondiciones:
        ``mapa`` es un ``folium.Map`` inicializado con un elemento raiz.
    Postcondiciones:
        Inserta una hoja de estilos en el encabezado del mapa y retorna
        ``None``.
    """
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
            .padron-selector-control label {
                display: block;
                margin-bottom: 8px;
                font-weight: 700;
            }
            .padron-selector-control select {
                width: 100%;
                padding: 6px 8px;
                border: 1px solid #aeb6bf;
                border-radius: 4px;
                background: #fff;
                font: inherit;
                cursor: pointer;
            }
            .padron-resumen {
                display: flex;
                gap: 12px;
                margin-top: 9px;
                padding-top: 8px;
                border-top: 1px solid #d8dde3;
                white-space: nowrap;
            }
            .buscador-escuelas-control {
                position: relative;
                width: min(360px, calc(100vw - 24px));
                padding: 8px;
                background: rgba(255, 255, 255, 0.97);
                border: 2px solid rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                box-shadow: 0 1px 5px rgba(0, 0, 0, 0.35);
                font: 13px/1.3 Arial, sans-serif;
            }
            .buscador-escuelas-control input {
                box-sizing: border-box;
                width: 100%;
                padding: 8px 10px;
                border: 1px solid #aeb6bf;
                border-radius: 4px;
                font: inherit;
            }
            .buscador-escuelas-resultados {
                display: none;
                max-height: 280px;
                margin-top: 6px;
                overflow-y: auto;
                border: 1px solid #d8dde3;
                border-radius: 4px;
                background: #fff;
            }
            .buscador-escuelas-resultado,
            .buscador-escuelas-sin-resultados {
                box-sizing: border-box;
                display: block;
                width: 100%;
                padding: 8px 10px;
                border: 0;
                border-bottom: 1px solid #eef1f4;
                background: #fff;
                color: #1f2933;
                font: inherit;
                text-align: left;
            }
            .buscador-escuelas-resultado {
                cursor: pointer;
            }
            .buscador-escuelas-resultado:hover,
            .buscador-escuelas-resultado:focus {
                background: #eaf4fb;
                outline: none;
            }
        </style>
    """
    mapa.get_root().header.add_child(folium.Element(css))


def _agregar_buscador_escuelas(
    mapa: folium.Map,
    registros: list[dict[str, str]],
) -> None:
    """Agrega un buscador que localiza marcadores en todas las capas.

    Precondiciones:
        ``mapa`` es un mapa Folium y cada elemento de ``registros`` contiene
        etiqueta, texto, padron y nombres JavaScript de marcador y capa.
    Postcondiciones:
        Agrega al mapa un control de busqueda por texto que activa la capa del
        resultado, centra su marcador y abre el popup; retorna ``None``.
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

    template = branca.element.Template(
        f"""
        {{% macro script(this, kwargs) %}}
        (function() {{
            var map = {mapa.get_name()};
            var escuelas = [{registros_js}];
            var capas = Array.from(new Set(escuelas.map(function(item) {{
                return item.capa;
            }})));

            function normalizar(valor) {{
                return String(valor || "")
                    .normalize("NFD")
                    .replace(/[\u0300-\u036f]/g, "")
                    .toLowerCase()
                    .trim();
            }}

            escuelas.forEach(function(item) {{
                item.textoNormalizado = normalizar(item.texto);
            }});

            var control = L.control({{position: "topleft"}});
            control.onAdd = function() {{
                var contenedor = L.DomUtil.create(
                    "div",
                    "buscador-escuelas-control"
                );
                var input = L.DomUtil.create("input", "", contenedor);
                input.type = "search";
                input.placeholder = "Buscar escuela, CUE, domicilio...";
                input.setAttribute("aria-label", "Buscar una escuela");

                var resultados = L.DomUtil.create(
                    "div",
                    "buscador-escuelas-resultados",
                    contenedor
                );

                function ocultarResultados() {{
                    resultados.style.display = "none";
                    resultados.innerHTML = "";
                }}

                function abrirEscuela(item) {{
                    var selectorPadron = document.querySelector(
                        '.padron-selector-control select[name="padron-selector"]'
                    );
                    if (selectorPadron) {{
                        selectorPadron.value = item.padron;
                        selectorPadron.dispatchEvent(new Event("change"));
                    }} else {{
                        capas.forEach(function(capa) {{
                            if (map.hasLayer(capa)) {{
                                map.removeLayer(capa);
                            }}
                        }});
                        map.addLayer(item.capa);
                    }}

                    if (typeof item.capa.zoomToShowLayer === "function") {{
                        item.capa.zoomToShowLayer(item.marcador, function() {{
                            map.setView(item.marcador.getLatLng(), 16);
                            item.marcador.openPopup();
                        }});
                    }} else {{
                        map.setView(item.marcador.getLatLng(), 16);
                        item.marcador.openPopup();
                    }}
                    input.value = item.etiqueta;
                    ocultarResultados();
                }}

                function mostrarResultados() {{
                    var consulta = normalizar(input.value);
                    resultados.innerHTML = "";
                    if (consulta.length < 2) {{
                        ocultarResultados();
                        return;
                    }}

                    var coincidencias = escuelas.filter(function(item) {{
                        return item.textoNormalizado.indexOf(consulta) !== -1;
                    }}).slice(0, 20);

                    if (!coincidencias.length) {{
                        var vacio = L.DomUtil.create(
                            "div",
                            "buscador-escuelas-sin-resultados",
                            resultados
                        );
                        vacio.textContent = "No se encontraron escuelas";
                    }} else {{
                        coincidencias.forEach(function(item) {{
                            var boton = L.DomUtil.create(
                                "button",
                                "buscador-escuelas-resultado",
                                resultados
                            );
                            boton.type = "button";
                            boton.textContent = item.etiqueta;
                            boton.addEventListener("click", function() {{
                                abrirEscuela(item);
                            }});
                        }});
                    }}
                    resultados.style.display = "block";
                }}

                input.addEventListener("input", mostrarResultados);
                input.addEventListener("keydown", function(event) {{
                    if (event.key === "Enter") {{
                        var primero = resultados.querySelector(
                            ".buscador-escuelas-resultado"
                        );
                        if (primero) {{
                            event.preventDefault();
                            primero.click();
                        }}
                    }} else if (event.key === "Escape") {{
                        ocultarResultados();
                    }}
                }});

                L.DomEvent.disableClickPropagation(contenedor);
                L.DomEvent.disableScrollPropagation(contenedor);
                return contenedor;
            }};
            control.addTo(map);
        }})();
        {{% endmacro %}}
        """
    )
    macro = branca.element.MacroElement()
    macro._template = template
    mapa.add_child(macro)


def crear_mapa(
    escuelas_por_padron: dict[str, pd.DataFrame] | pd.DataFrame,
    limite_dolores: str,
    descripciones: dict[str, str],
) -> folium.Map:
    """Construye el mapa interactivo de escuelas de Dolores.

    Precondiciones:
        ``escuelas_por_padron`` es un ``DataFrame`` o un diccionario de ellos
        que cumple el contrato de :func:`_crear_capa_escuelas`;
        ``limite_dolores`` contiene GeoJSON valido y ``descripciones`` mapea
        Cueanexos a textos.
    Postcondiciones:
        Retorna un nuevo ``folium.Map`` con limite, capas, minimapa y visor de
        coordenadas; agrega el selector cuando existe al menos una capa y no
        modifica los argumentos recibidos.
    """
    if isinstance(escuelas_por_padron, pd.DataFrame):
        nombre = _etiqueta_padron(_nombre_padron(PADRON_PATH))
        escuelas_por_padron = {nombre: escuelas_por_padron}

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
            descripciones,
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
