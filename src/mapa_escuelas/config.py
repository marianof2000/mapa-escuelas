# -*- coding: utf-8 -*-
"""Configuracion del generador de mapas."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PADRONES_DIR = DATA_DIR / "padrones"

LIMITES_PATH = DATA_DIR / "limite_partidos.geojson"
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

# Esta escuela cerró antes de 2011
EP_12 = {
    "padron": "padron_2010",
    "padron_nombre": "Padrón 2010",
    "padron_archivo": "2010_padron_oficial_establecimientos_educativos.xlsx",
    "Jurisdicción": "Buenos Aires",
    "Cueanexo": "60200000",
    "Nombre": "ESCUELA PRIMARIA N°12 OLEGARIO V. ANDRADE",
    "Sector": "Estatal",
    "Ámbito": "Rural",
    "Domicilio": "Ruta 63 KM 20",
    "C. P.": "B7100",
    "Código de área": None,
    "Teléfono": "441234",
    "Código de localidad": "6238025.1",
    "Localidad": "DOLORES",
    "Departamento": "DOLORES",
    "Mail": None,
    "nombre": 'ESCUELA DE EDUCACIÓN PRIMARIA Nº12 "OLEGARIO V. ANDRADE"',
    "id_modalidad": 1,
    "modalidad": "Educación Común",
    "id_nivel": 2,
    "nivel": "Nivel Primario",
    "id_periodo": 103,
    "periodo": None,
    "calle": "RUTA 63 KM 20",
    "nro": "S/N",
    "localidad": "DOLORES",
    "codigo_postal": "7100.1",
    "nro_escuela": 12,
    "latitud": -36.31279,
    "longitud": -57.474213,
    "Código de departamento": None,
    "Cue": None,
}

COORDENADAS_OFICIALES = {
    # Escuela Nº27 Sargento Cabral: https://maps.app.goo.gl/Gc4M5nnzzdq3H2iG9
    60828000: (-36.4252262, -57.4676075),
    # Escuela Nº12 Olegario V. Andrade: https://maps.app.goo.gl/bexbi8wrMq9CggYU6
    60200000: (-36.31279, -57.474213),
}
