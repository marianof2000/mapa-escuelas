# -*- coding: utf-8 -*-
"""Configuracion del generador de mapas."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PADRONES_DIR = DATA_DIR / "padrones"

PADRON_PATH = PADRONES_DIR / "2026_padron_oficial_establecimientos_educativos.xlsx"
LIMITES_PATH = DATA_DIR / "limite_partidos.geojson"
DESCRIPCIONES_PATH = DATA_DIR / "descripciones_escuelas.json"
OUTPUT_PATH = BASE_DIR / "maps-dol.html"
PADRONES_CSV_PATH = DATA_DIR / "padrones.csv"
LINKS_PATH = DATA_DIR / "links.csv"
HISTORIAS_PATH = DATA_DIR / "indice_escuelas_rurales_dolores_CUE.csv"

IMAGENES_POPUP_PATH = BASE_DIR / "img"
IMAGEN_WEB_PATH = "img"
IMAGEN_EXTENSION = ".webp"
IMAGEN_MUESTRA = "escuela-muestra.webp"

PADRON_COLUMNAS_REQUERIDAS = {
    "Cueanexo",
    "Jurisdicción",
    "Sector",
    "Primario",
    "Localidad",
    "Departamento",
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

COORDENADAS_OFICIALES = {
    # Escuela Nº27 Sargento Cabral: https://maps.app.goo.gl/Gc4M5nnzzdq3H2iG9
    60828000: (-36.4252262, -57.4676075),
    # Escuela Nº12 Olegario V andrade: https://maps.app.goo.gl/bexbi8wrMq9CggYU6
    00000000: (-36.31279,-57.474213)
}
