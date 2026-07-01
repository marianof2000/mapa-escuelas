# -*- coding: utf-8 -*-
"""Configuracion del generador de mapas."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PADRONES_DIR = DATA_DIR / "padrones"

PADRON_PATH = PADRONES_DIR / "2026.01.12_padron_oficial_establecimientos_educativos_die.xlsx"
LIMITES_PATH = DATA_DIR / "limite_partidos.geojson"
DESCRIPCIONES_PATH = DATA_DIR / "descripciones_escuelas.json"
OUTPUT_PATH = BASE_DIR / "maps-dol.html"
PADRONES_CSV_PATH = DATA_DIR / "padrones.csv"

IMAGENES_POPUP_PATH = BASE_DIR / "img"
IMAGEN_WEB_PATH = "img"
IMAGEN_EXTENSION = ".webp"

PADRON_COLUMNAS_REQUERIDAS = {
    "Cueanexo",
    "Jurisdicción",
    "Primario",
    "Localidad",
    "Mail",
}
PADRON_FILAS_DE_BUSQUEDA = 30

PRIMARIA_URL = (
    "https://github.com/marianof2000/datasets/raw/main/" "Nivel_Primario_G_Estatal.csv"
)
PRIMARIA_COLUMNAS = (
    "cueanexo",
    "nombre",
    "id_modalidad",
    "modalidad",
    "id_nivel",
    "nivel",
    "id_periodo",
    "periodo",
    "calle",
    "nro",
    "localidad",
    "codigo_postal",
    "nro_escuela",
    "latitud",
    "longitud",
)

SPOTIFY_URL = (
    "https://open.spotify.com/embed/show/" "446QK5WSDCmetKGYV38zoi?utm_source=generator"
)
