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
- `src/mapa_escuelas/datos.py`: carga, normaliza y combina las fuentes.
- `src/mapa_escuelas/popups.py`: construye las fichas de las escuelas.
- `src/mapa_escuelas/controles.py`: construye las capas, el selector, el
  resumen y el buscador.
- `src/mapa_escuelas/plantillas.py`: carga y almacena en caché las plantillas
  de los controles.
- `src/mapa_escuelas/templates/`: contiene el CSS y JavaScript/Jinja de la
  interfaz del mapa.
- `src/mapa_escuelas/mapa.py`: compone el mapa Folium.
- `src/mapa_escuelas/config.py`: contiene rutas, URLs y coordenadas oficiales.
- `data/padrones/`: padrones oficiales en formato XLSX, de 2010 a 2026.
- `data/padrones.csv`: padrón consolidado que utiliza el mapa.
- `data/links.csv`: un enlace único asociado a cada `Cueanexo`.
- `data/indice_escuelas_rurales_dolores_CUE.csv`: historias de las escuelas,
  relacionadas mediante `Cueanexo`.
- `data/limite_partidos.geojson`: límite geográfico del partido de Dolores.
- `img/`: fotografías de las escuelas y miniatura genérica.
- `tests/test_datos.py`: pruebas de lectura, validación y combinación de fuentes.
- `tests/test_convertir.py`: pruebas de las estrategias de coordenadas.
- `tests/test_mapa.py`: pruebas de composición y controles del mapa.
- `tests/test_popups.py`: pruebas de las fichas emergentes.
- `tests/test_contratos.py`: controla type hints y contratos de todas las
  funciones Python.
- `maps-dol.html`: mapa generado.
- `index.html`: página contenedora que muestra el mapa en un `iframe`.

## Responsabilidades de los módulos Python

El flujo principal de dependencias es:

```text
config → datos → popups → controles → mapa → generar_mapa
              └────────→ convertir
```

### Paquete `src.mapa_escuelas`

#### `config.py`

Centraliza la configuración que comparten los demás módulos:

- rutas de los XLSX, CSV, GeoJSON, imágenes y HTML de salida;
- columnas obligatorias de los padrones y del CSV de escuelas primarias;
- URL de la fuente remota de coordenadas;
- URL del reproductor de Spotify;
- coordenadas oficiales confirmadas manualmente.

No carga archivos ni construye el mapa. Los cambios de ubicación de las
fuentes deben realizarse aquí para evitar rutas duplicadas en el código.

#### `datos.py`

Es la capa de acceso y preparación de datos. Sus responsabilidades son:

- localizar los libros XLSX disponibles;
- detectar la hoja y la fila de encabezados de cada padrón;
- leer los XLSX mediante pandas y Calamine;
- filtrar escuelas primarias estatales del partido de Dolores;
- normalizar `Cueanexo` para usarlo como clave entre fuentes;
- normalizar el nombre visible de cada pin desde `nombre` o `Nombre`;
- cargar `padrones.csv`, `links.csv` y las historias;
- validar columnas, claves duplicadas y enlaces faltantes;
- unir enlaces e historias con cada marcador;
- cargar y recortar el GeoJSON al límite del partido de Dolores.

Este módulo entrega datos preparados, pero no genera HTML ni objetos Folium.

#### `convertir.py`

Implementa el proceso de construcción de `data/padrones.csv` a partir de los
XLSX. Recorre los padrones, utiliza las funciones de `datos.py`, agrega los
identificadores de período y completa coordenadas faltantes.

La estrategia para completar coordenadas es:

1. coordenada oficial configurada manualmente;
2. coordenada más reciente del mismo `Cueanexo`;
3. coordenada de una escuela con igual departamento, localidad y domicilio.

También contiene la interfaz de línea de comandos y sus opciones
`--padrones-dir`, `--salida` y `--primaria-url`.

#### `popups.py`

Construye las fichas emergentes de los marcadores. Se ocupa de:

- separar la denominación de la escuela de su nombre propio;
- localizar la imagen WebP correspondiente al CUE;
- utilizar la miniatura genérica cuando no existe una imagen propia;
- escapar el contenido proveniente de los archivos de datos;
- generar el HTML de ubicación, ámbito, historia, enlace, imagen
  y reproductor;
- convertir ese HTML en un `folium.Popup`.

No decide qué escuelas aparecen ni crea capas del mapa.

#### `controles.py`

Contiene los componentes interactivos asociados a las capas:

- crea un marcador por escuela y los agrupa con `MarkerCluster`;
- asigna colores diferentes a escuelas rurales y urbanas;
- prepara el contenido indexado por el buscador;
- genera el selector desplegable de padrones;
- actualiza el resumen de escuelas rurales y urbanas;
- activa la capa correcta cuando se selecciona un resultado.

Recibe datos ya preparados y delega la ficha de cada marcador a `popups.py`.

#### `plantillas.py` y `templates/`

`plantillas.py` localiza y carga una sola vez los recursos de interfaz. El
directorio `templates/` mantiene separados de Python:

- `controles.css`: estilos del selector, resumen y buscador;
- `popups.css`: estilos compartidos por todas las fichas emergentes;
- `selector_padrones.js.jinja`: comportamiento del selector de padrones;
- `buscador_escuelas.js.jinja`: búsqueda, cambio de capa y apertura de fichas.

Las plantillas forman parte del paquete instalado mediante la configuración de
`package-data` de `pyproject.toml`.

#### `mapa.py`

Compone el objeto `folium.Map` final. Ordena los padrones desde el más reciente
al más antiguo, selecciona 2026 al iniciar, calcula los resúmenes por ámbito y
conecta las capas con los controles.

También agrega el límite geográfico de Dolores, el minimapa, la escala y el
visor de coordenadas. Retorna el mapa en memoria; no escribe el archivo HTML.

#### `generar_mapa.py`

Es el punto de entrada para generar el resultado publicable. Coordina estas
operaciones:

1. cargar el límite geográfico;
2. cargar las escuelas agrupadas por padrón;
3. construir el mapa mediante `mapa.py`;
4. guardar el resultado en `maps-dol.html`.

Puede ejecutarse con:

```bash
python3 -m src.mapa_escuelas.generar_mapa
```

#### `__init__.py`

Identifica `mapa_escuelas` como paquete y contiene su descripción general. No
ejecuta procesos ni expone estado mutable.

### Dónde agregar cambios

- Nuevas fuentes, validaciones o cruces de datos: `datos.py`.
- Reglas para completar coordenadas durante la conversión: `convertir.py`.
- Contenido o diseño de las fichas: `popups.py`.
- Selector, buscador, capas o resúmenes: `controles.py`.
- Estilos o comportamiento JavaScript de los controles: `templates/`.
- Configuración general del mapa y componentes Folium: `mapa.py`.
- Rutas, URLs y constantes compartidas: `config.py`.
- Secuencia para generar el archivo final: `generar_mapa.py`.

### Convenciones de las funciones Python

Toda función o método nuevo o modificado debe declarar type hints para cada
parámetro y para el valor de retorno. Su docstring también debe incluir
secciones explícitas de `Precondiciones:` y `Postcondiciones:` que describan
los requisitos de entrada, los efectos, el resultado y los errores relevantes.

## Requisitos

- Python 3.12 o posterior.
- Acceso a internet durante la conversión de los padrones para descargar el
  CSV de escuelas primarias definido en `PRIMARIA_URL`.
- Acceso a internet al visualizar el mapa para cargar Leaflet,
  OpenStreetMap, Bootstrap y Spotify.

Instalar las dependencias:

```bash
python3 -m pip install .
```

También se puede instalar el proyecto con `uv`:

```bash
uv sync
```

La instalación incorpora los comandos:

```bash
mapa-escuelas-generar
mapa-escuelas-convertir
```

## Fuentes necesarias para generar el mapa

El generador espera los siguientes archivos:

- `data/padrones.csv`
- `data/links.csv`
- `data/indice_escuelas_rurales_dolores_CUE.csv`
- `data/limite_partidos.geojson`

`data/padrones.csv` y `data/limite_partidos.geojson` están versionados para que
un clon nuevo pueda regenerar `maps-dol.html` sin descargar los XLSX. Los
libros de Excel solo se necesitan para reconstruir `padrones.csv` y permanecen
fuera de Git debido a su tamaño.

## Convertir los padrones XLSX

Para consolidar los libros de `data/padrones/`:

```bash
python3 -m src.mapa_escuelas.convertir
```

Con el proyecto instalado, puede usarse el comando:

```bash
mapa-escuelas-convertir
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
mapa-escuelas-convertir \
  --padrones-dir data/padrones \
  --salida data/padrones.csv
```

## Enlaces

`data/links.csv` debe contener una sola fila por `Cueanexo` y estas columnas:

```text
Cueanexo,link,Nombre
```

La combinación se realiza únicamente mediante `Cueanexo`, por lo que el mismo
enlace se reutiliza en todos los padrones donde aparece la escuela. La
columna `Nombre` facilita la identificación manual de cada fila, pero no se usa
como clave. La generación se detiene si falta un enlace o nombre, o si hay CUE
duplicados.

## Historias

Las historias se toman de la columna `historia` de
`data/indice_escuelas_rurales_dolores_CUE.csv` y se relacionan con cada escuela
mediante `Cueanexo`.

Cuando el CSV no contiene una historia para un CUE, la ficha muestra
`Historia no disponible.`. Las filas de la fuente histórica que no tienen CUE
no pueden asociarse automáticamente con un marcador.

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

Con el proyecto instalado, también se puede ejecutar:

```bash
mapa-escuelas-generar
```

El resultado se guarda en `maps-dol.html`.

Si se agregan o modifican padrones XLSX, primero hay que volver a ejecutar la
conversión y luego regenerar el mapa.

## Validar el proyecto

Las pruebas no requieren internet una vez sincronizado el entorno:

```bash
uv run pytest -q
```

Las validaciones comprueban, entre otros puntos, la lectura de padrones, las
coordenadas, las imágenes, los enlaces, las historias, el selector desplegable,
el orden de los años, el resumen rural/urbano, el buscador y que todas las
funciones Python tengan type hints y contratos completos.

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
