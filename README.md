# Mapa de escuelas primarias de Dolores

Este proyecto genera `maps-dol.html`, un mapa interactivo de las escuelas
primarias estatales del partido de Dolores, provincia de Buenos Aires. Está
desarrollado con Python, pandas, Calamine y Folium.

El mapa reúne los padrones de 2010 a 2026. Permite consultar un solo padrón por
vez, buscar escuelas y abrir una ficha por cada marcador con sus datos,
historia, enlace, imagen y reproductor de Spotify.

## Funciones del mapa

- Selector desplegable de padrones, ordenado desde 2026 hacia los años
  anteriores.
- Padrón 2026 seleccionado al iniciar.
- El padrón 2010 se presenta como `Anterior a 2011`.
- Resumen dinámico de la cantidad de escuelas rurales y urbanas del padrón
  activo.
- Buscador por escuela, CUE, domicilio, localidad y demás datos disponibles.
- Marcadores naranjas para escuelas rurales y celestes para escuelas urbanas.
- Ficha ampliada para cada escuela con ubicación, ámbito, historia, enlace,
  imagen y audio.
- Miniatura genérica cuando una escuela no tiene una imagen propia.
- Cambio automático de padrón cuando se abre un resultado del buscador.

## Estructura principal

- `src/mapa_escuelas/generar_mapa.py`: genera el mapa HTML.
- `src/mapa_escuelas/convertir.py`: consolida los padrones XLSX en un CSV.
- `src/mapa_escuelas/funciones.py`: carga los datos y construye los controles,
  capas, marcadores y fichas.
- `src/mapa_escuelas/config.py`: contiene rutas, URLs y coordenadas oficiales.
- `data/padrones/`: padrones oficiales en formato XLSX, de 2010 a 2026.
- `data/padrones.csv`: padrón consolidado que utiliza el mapa.
- `data/links.csv`: enlace asociado a cada marcador.
- `data/indice_escuelas_rurales_dolores_CUE.csv`: historias de las escuelas,
  relacionadas mediante `Cueanexo`.
- `data/descripciones_escuelas.json`: descripciones opcionales por CUE.
- `data/limite_partidos.geojson`: límite geográfico del partido de Dolores.
- `img/`: fotografías de las escuelas y miniatura genérica.
- `tests/test_validacion.py`: pruebas automatizadas del proyecto.
- `maps-dol.html`: mapa generado.
- `index.html`: página contenedora que muestra el mapa en un `iframe`.

Los archivos `mapas.py`, `convertir.py` y
`mapas_escuelas_dolores_taller_producción_de_obra_vero.py` se conservan como
wrappers de compatibilidad para ejecutar el proyecto desde la raíz.

## Requisitos

- Python 3.12 o posterior.
- Acceso a internet durante la conversión de los padrones para descargar el
  CSV de escuelas primarias definido en `PRIMARIA_URL`.
- Acceso a internet al visualizar el mapa para cargar Leaflet,
  OpenStreetMap, Bootstrap y Spotify.

Instalar las dependencias:

```bash
python3 -m pip install -r requirements.txt
```

También se puede instalar el proyecto con `uv`:

```bash
uv sync
```

## Fuentes necesarias para generar el mapa

El generador espera los siguientes archivos:

- `data/padrones.csv`
- `data/links.csv`
- `data/indice_escuelas_rurales_dolores_CUE.csv`
- `data/descripciones_escuelas.json`
- `data/limite_partidos.geojson`

La generación de `maps-dol.html` no abre los XLSX ni descarga información
remota. Los libros de Excel solo se procesan al ejecutar la conversión.

## Convertir los padrones XLSX

Para consolidar los libros de `data/padrones/`:

```bash
python3 -m src.mapa_escuelas.convertir
```

También puede usarse el wrapper:

```bash
python3 convertir.py
```

El resultado se guarda en `data/padrones.csv`. Cada fila incluye el
identificador y nombre del padrón, el archivo de origen, el CUE, los datos de la
escuela y las coordenadas utilizadas por el mapa.

Los XLSX se leen mediante pandas con el motor Calamine. Si una escuela no tiene
coordenadas en un padrón histórico, el conversor intenta completarlas en este
orden:

1. Coordenadas oficiales configuradas manualmente.
2. Coordenadas más recientes del mismo `Cueanexo`.
3. Coordenadas de una escuela con el mismo departamento, localidad y
   domicilio.

La conversión se detiene si todavía quedan escuelas sin ubicación.

Para indicar otras rutas:

```bash
python3 convertir.py \
  --padrones-dir data/padrones \
  --salida data/padrones.csv
```

## Enlaces

`data/links.csv` debe contener una fila por marcador y estas columnas:

```text
padron,Cueanexo,link
```

La combinación se realiza mediante el identificador del padrón y el
`Cueanexo`. La generación se detiene si falta un enlace o si hay claves
duplicadas.

## Historias

Las historias se toman de la columna `historia` de
`data/indice_escuelas_rurales_dolores_CUE.csv` y se relacionan con cada escuela
mediante `Cueanexo`.

Cuando el CSV no contiene una historia para un CUE, la ficha muestra
`Historia no disponible.`. Las filas de la fuente histórica que no tienen CUE
no pueden asociarse automáticamente con un marcador.

## Descripciones

Las descripciones opcionales se editan en
`data/descripciones_escuelas.json`, utilizando el `Cueanexo` como clave:

```json
{
  "60828200": "Texto descriptivo de la escuela."
}
```

Si una escuela no tiene descripción, ese bloque no aparece en la ficha.

## Imágenes

Las imágenes se guardan en `img/` en formato WebP. El nombre debe coincidir con
el `Cueanexo` de la escuela:

```text
img/60828200.webp
```

Si no existe una imagen específica, el mapa utiliza
`img/escuela-muestra.webp`. Las imágenes no se incrustan dentro del HTML: las
fichas las cargan mediante rutas relativas.

## Generar el mapa

Después de preparar los CSV:

```bash
python3 -m src.mapa_escuelas.generar_mapa
```

También se puede ejecutar:

```bash
python3 mapas_escuelas_dolores_taller_producción_de_obra_vero.py
```

El resultado se guarda en `maps-dol.html`.

Si se agregan o modifican padrones XLSX, primero hay que volver a ejecutar la
conversión y luego regenerar el mapa.

## Validar el proyecto

Las pruebas no requieren internet:

```bash
python3 -m unittest discover -s tests -v
```

Las validaciones comprueban, entre otros puntos, la lectura de padrones, las
coordenadas, las imágenes, los enlaces, las historias, el selector desplegable,
el orden de los años, el resumen rural/urbano y el buscador.

## Publicación

Para publicar el resultado se deben subir:

- `maps-dol.html`
- `index.html`, si se utiliza la página contenedora
- la carpeta `img/`

Los CSV y XLSX no son necesarios para visualizar un mapa que ya fue generado.

## Fuentes de datos

- [Padrón oficial de establecimientos educativos](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/padron-oficial-de-establecimientos-educativos)
- [Datos Argentina: padrón oficial](https://datos.gob.ar/dataset/padron-oficial-de-establecimientos-educativos)
- [CSV de nivel primario estatal](https://github.com/marianof2000/datasets/raw/main/Nivel_Primario_G_Estatal.csv)
- [Ubicación de la Escuela Primaria N.º 12](https://maps.app.goo.gl/bexbi8wrMq9CggYU6)
- [Ubicación de la Escuela Primaria N.º 27](https://maps.app.goo.gl/Gc4M5nnzzdq3H2iG9)
