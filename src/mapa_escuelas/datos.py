# -*- coding: utf-8 -*-
"""Carga, normalización y combinación de las fuentes de datos."""
from decimal import Decimal, InvalidOperation
import json
import logging
from pathlib import Path
import re
import pandas as pd
from .config import (
    HISTORIAS_PATH, LINKS_PATH, LIMITES_PATH,
    PADRONES_CSV_PATH, PADRONES_DIR, PADRON_COLUMNAS_REQUERIDAS,
    PADRON_FILAS_DE_BUSQUEDA, PRIMARIA_COLUMNAS, PRIMARIA_URL,
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
    """Localiza la hoja y la fila de encabezado en un libro ya abierto.

    Precondiciones:
        ``excel`` referencia un libro abierto y legible; ``path`` identifica
        ese libro para construir mensajes de error.
    Postcondiciones:
        Retorna la primera hoja compatible y un indice de fila no negativo;
        lanza ``ValueError`` si no encuentra todas las columnas requeridas.
    """
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
    """Devuelve la etiqueta visible correspondiente a un padron.

    Precondiciones:
        ``nombre`` es una cadena que identifica un padron.
    Postcondiciones:
        Retorna ``Anterior a 2011`` para el padron 2010 o la misma cadena
        recibida para cualquier otro valor; no modifica el argumento.
    """
    if nombre in {"2010", "Padrón 2010"}:
        return "Anterior a 2011"
    return nombre

def _anio_para_ordenar_padron(nombre: str) -> int:
    """Obtiene el anio usado para ordenar las etiquetas de padrones.

    Precondiciones:
        ``nombre`` es una cadena que puede contener un anio de cuatro digitos.
    Postcondiciones:
        Retorna 2010 para ``Anterior a 2011``, el primer anio reconocido o
        ``-1`` cuando la cadena no contiene un anio compatible.
    """
    if nombre == "Anterior a 2011":
        return 2010
    coincidencia = re.search(r"20\d{2}", nombre)
    return int(coincidencia.group()) if coincidencia else -1

def _normalizar_cueanexo(valor: object) -> str:
    """Normaliza un Cueanexo para usarlo como clave entre archivos CSV.

    Precondiciones:
        ``valor`` admite conversion a texto.
    Postcondiciones:
        Retorna una cadena decimal sin ceros fraccionarios innecesarios cuando
        el valor es numerico o su representacion limpia cuando no lo es.
    """
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
    padrones, links, historias = _cargar_fuentes_mapa(
        path,
        links_path,
        historias_path,
    )
    padrones = _normalizar_nombre_escuela(padrones, path)
    _validar_columnas_requeridas(
        padrones,
        {
            "padron",
            "padron_nombre",
            "Cueanexo",
            "nombre",
            "latitud",
            "longitud",
            "Domicilio",
            "Ámbito",
        },
        path,
    )
    _validar_columnas_requeridas(
        links,
        {"Cueanexo", "link", "Nombre"},
        links_path,
    )
    _validar_columnas_requeridas(
        historias,
        {"Cueanexo", "historia"},
        historias_path,
    )

    padrones_con_links = _incorporar_links(padrones, links, links_path)
    padrones_completos = _incorporar_historias(
        padrones_con_links,
        historias,
        historias_path,
    )
    return _agrupar_escuelas_por_padron(padrones_completos, path)


def _cargar_fuentes_mapa(
    path: Path,
    links_path: Path,
    historias_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Lee los tres CSV necesarios para construir las capas del mapa.

    Precondiciones:
        Las rutas recibidas identifican archivos CSV legibles.
    Postcondiciones:
        Retorna nuevos ``DataFrame`` de padrones, enlaces e historias; lanza
        ``FileNotFoundError`` indicando la primera fuente inexistente.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path}. Ejecuta `mapa-escuelas-convertir` primero."
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
    return padrones, links, historias


def _normalizar_nombre_escuela(
    padrones: pd.DataFrame,
    path: Path,
) -> pd.DataFrame:
    """Unifica ``nombre`` y ``Nombre`` para construir los pines del mapa.

    Precondiciones:
        ``padrones`` representa el contenido leido desde ``path``.
    Postcondiciones:
        Retorna una copia con ``nombre`` completo y sin espacios exteriores,
        priorizando esa columna y usando ``Nombre`` como alternativa; lanza
        ``ValueError`` si no existe ninguna o quedan filas sin denominacion.
    """
    columnas_disponibles = {"nombre", "Nombre"} & set(padrones.columns)
    if not columnas_disponibles:
        raise ValueError(
            f"Falta una columna de nombre de escuela en {path}: nombre o Nombre"
        )

    resultado = padrones.copy()
    if "nombre" in resultado.columns:
        nombres = resultado["nombre"].fillna("").astype(str).str.strip()
    else:
        nombres = pd.Series("", index=resultado.index, dtype="string")

    if "Nombre" in resultado.columns:
        nombres_alternativos = (
            resultado["Nombre"].fillna("").astype(str).str.strip()
        )
        nombres = nombres.mask(nombres.eq(""), nombres_alternativos)

    sin_nombre = nombres.eq("")
    if sin_nombre.any():
        cantidad = int(sin_nombre.sum())
        raise ValueError(f"Falta el nombre de {cantidad} escuelas en {path}")

    resultado["nombre"] = nombres
    return resultado


def _validar_columnas_requeridas(
    datos: pd.DataFrame,
    columnas_requeridas: set[str],
    path: Path,
) -> None:
    """Valida la presencia de un conjunto de columnas en una fuente.

    Precondiciones:
        ``datos`` representa el contenido de ``path`` y
        ``columnas_requeridas`` contiene nombres de columnas no vacios.
    Postcondiciones:
        Retorna ``None`` si estan todas las columnas; lanza ``ValueError`` con
        la lista ordenada de faltantes en caso contrario.
    """
    columnas_faltantes = sorted(columnas_requeridas - set(datos.columns))
    if columnas_faltantes:
        faltantes = ", ".join(columnas_faltantes)
        raise ValueError(f"Faltan columnas en {path}: {faltantes}")


def _incorporar_links(
    padrones: pd.DataFrame,
    links: pd.DataFrame,
    links_path: Path,
) -> pd.DataFrame:
    """Une cada marcador con el enlace unico de su CUE.

    Precondiciones:
        ``padrones`` y ``links`` contienen ``Cueanexo``; ``links`` tambien
        contiene ``link`` y ``Nombre`` y sus columnas ya fueron validadas.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` con un enlace no vacio por marcador;
        lanza ``ValueError`` ante CUE duplicados, enlaces faltantes o nombres
        de referencia vacios.
    """
    padrones = padrones.copy()
    links = links.copy()
    padrones["_cue_link"] = padrones["Cueanexo"].map(_normalizar_cueanexo)
    links["_cue_link"] = links["Cueanexo"].map(_normalizar_cueanexo)
    if links.duplicated(subset="_cue_link").any():
        raise ValueError(f"Hay enlaces duplicados en {links_path}")
    nombres_vacios = links["Nombre"].isna() | links["Nombre"].str.strip().eq("")
    if nombres_vacios.any():
        cantidad = int(nombres_vacios.sum())
        raise ValueError(f"Faltan nombres para {cantidad} CUE en {links_path}")

    padrones = pd.merge(
        padrones,
        links.loc[:, ["_cue_link", "link"]],
        how="left",
        on="_cue_link",
        validate="many_to_one",
    ).drop(columns="_cue_link")
    sin_link = padrones["link"].isna() | padrones["link"].str.strip().eq("")
    if sin_link.any():
        cantidad = int(sin_link.sum())
        raise ValueError(f"Faltan enlaces para {cantidad} marcadores en {links_path}")
    return padrones


def _incorporar_historias(
    padrones: pd.DataFrame,
    historias: pd.DataFrame,
    historias_path: Path,
) -> pd.DataFrame:
    """Une cada escuela con su historia mediante el CUE normalizado.

    Precondiciones:
        ``padrones`` contiene ``Cueanexo`` e ``historias`` contiene
        ``Cueanexo`` e ``historia``; sus columnas ya fueron validadas.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` con historia no vacia en cada fila;
        lanza ``ValueError`` si la fuente posee CUE duplicados no vacios.
    """
    padrones = padrones.copy()
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
    return padrones


def _agrupar_escuelas_por_padron(
    padrones: pd.DataFrame,
    path: Path,
) -> dict[str, pd.DataFrame]:
    """Agrupa las escuelas localizadas bajo su etiqueta visible de padron.

    Precondiciones:
        ``padrones`` contiene ``padron_nombre``, ``latitud`` y ``longitud``;
        ``path`` identifica la fuente para informar errores.
    Postcondiciones:
        Retorna un diccionario no vacio de copias sin coordenadas faltantes;
        lanza ``ValueError`` si ninguna escuela puede incorporarse al mapa.
    """
    padrones = padrones.dropna(subset=["latitud", "longitud"])
    escuelas_por_padron: dict[str, pd.DataFrame] = {}
    for padron, escuelas in padrones.groupby("padron_nombre", sort=False):
        escuelas_por_padron[_etiqueta_padron(str(padron))] = escuelas.copy()

    if not escuelas_por_padron:
        raise ValueError(f"No hay escuelas con coordenadas en {path}")

    return escuelas_por_padron
