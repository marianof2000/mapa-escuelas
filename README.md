# Mapa de escuelas primarias de Dolores

Este proyecto genera `maps-dol.html`, un mapa interactivo de escuelas primarias
de Dolores hecho con Folium. El mapa lee las escuelas desde `data/padrones.csv`,
crea una capa por cada padron disponible y permite seleccionar una sola capa por
vez con botones de radio.
Cada marcador abre un popup con datos de la escuela, una descripcion editable,
una imagen ilustrativa y un reproductor de Spotify.

## Archivos principales

- `src/mapa_escuelas/`: paquete Python del proyecto.
- `src/mapa_escuelas/generar_mapa.py`: script principal que genera el mapa.
- `src/mapa_escuelas/funciones.py`: funciones de carga de datos, armado de
  popups y construccion del mapa.
- `src/mapa_escuelas/config.py`: rutas, URLs y columnas esperadas.
- `src/mapa_escuelas/convertir.py`: genera `data/padrones.csv` desde los
  padrones `.xlsx`.
- `mapas.py`, `convertir.py` y
  `mapas_escuelas_dolores_taller_producción_de_obra_vero.py`: wrappers de
  compatibilidad para ejecutar el proyecto desde la raiz.
- `data/descripciones_escuelas.json`: textos de descripcion por escuela. La
  clave es el `Cueanexo`.
- `data/padrones.csv`: CSV consolidado que usa el generador del mapa.
- `data/padrones/`: archivos `.xlsx` fuente.
- `data/limite_partidos.geojson`: limite geografico usado en el mapa.
- `tests/`: validaciones del proyecto.
- `img/`: imagenes de los popups. Cada archivo debe llamarse con el `Cueanexo`
  correspondiente, por ejemplo `img/60828200.webp`.
- `maps-dol.html`: mapa generado.
- `index.html`: pagina contenedora que muestra `maps-dol.html` en un iframe.

## Requisitos

Instalar dependencias:

```bash
python3 -m pip install -r requirements.txt
```

El proyecto espera estos datos fuente:

- `data/padrones.csv`, generado con `convertir.py`
- `data/limite_partidos.geojson`
- `data/descripciones_escuelas.json`

La generacion del mapa no abre archivos `.xlsx` ni descarga datos remotos. La
conexion a internet solo hace falta al ejecutar `convertir.py`, porque ese
script descarga el CSV remoto definido en `PRIMARIA_URL`.

## Convertir padrones a CSV

Para consolidar todos los padrones `.xlsx` en un unico CSV:

```bash
python3 convertir.py
```

El resultado se guarda en `data/padrones.csv`. Cada fila incluye:

- `padron`: identificador estable del padron, por ejemplo `padron_2026_01`
- `padron_nombre`: etiqueta legible del padron, por ejemplo `Padrón 2026.01`
- `padron_archivo`: archivo `.xlsx` de origen
- columnas de escuelas primarias usadas para coordenadas y nombre
- columnas del padron necesarias para el popup y los filtros del mapa

Si una escuela no tiene coordenadas en un padron historico, el conversor busca
el registro mas reciente del mismo `Cueanexo` que tenga latitud y longitud. Como
segundo respaldo, utiliza el dato mas reciente de otra escuela con el mismo
departamento, localidad y domicilio. Si aun asi no puede resolver la ubicacion,
la conversion se detiene y no genera un CSV incompleto.

Las coordenadas oficiales confirmadas manualmente prevalecen sobre esos cruces.
La Escuela Nº27 Sargento Cabral (`Cueanexo 60828000`) utiliza la ubicacion
publicada en <https://maps.app.goo.gl/Gc4M5nnzzdq3H2iG9>.

Tambien se puede elegir directorio o salida:

```bash
python3 convertir.py --padrones-dir data/padrones --salida data/padrones.csv
```

Con la estructura actual, el directorio por defecto de padrones es
`data/padrones/`. Si queres usar otra carpeta, pasala con `--padrones-dir`.

## Descripciones

Las descripciones se editan en `data/descripciones_escuelas.json`.

Ejemplo:

```json
{
  "60828200": "Texto descriptivo de la escuela."
}
```

Si una escuela no tiene descripcion en el JSON, el popup muestra
`Descripcion pendiente.`.

## Imagenes

Las imagenes van en `img/` y se asocian automaticamente por `Cueanexo`.
El mapa lee archivos `.webp` directamente desde `img/`.

Ejemplo:

```text
img/60828200.webp
```

Al generar el mapa, las imagenes no se embeben dentro de `maps-dol.html`.
Los popups apuntan a rutas como `img/60828200.webp`.

## Generar el mapa

```bash
python3 mapas_escuelas_dolores_taller_producción_de_obra_vero.py
```

El resultado se guarda en `maps-dol.html`.

El generador del mapa usa solamente `data/padrones.csv` como fuente de escuelas.
Si agregas o cambias archivos `.xlsx`, primero hay que volver a ejecutar
`python3 convertir.py`.

El mapa incluye un selector de padrones en la esquina superior derecha. Cada
opcion es excluyente: al elegir un padron, se ocultan los marcadores del resto.
Los padrones se muestran con nombres cortos como `2021`, `2023.09` o `2026.01`.

El buscador de la esquina superior izquierda localiza escuelas en todos los
padrones por nombre, CUE, domicilio, localidad o cualquier otro dato disponible.
Al elegir un resultado, activa el padron correspondiente, centra la escuela y
abre su ficha. La busqueda no distingue mayusculas ni tildes.

## Validar el proyecto

Hay validaciones basicas que no requieren internet:

```bash
python3 -m unittest tests/test_validacion.py
```

Estas pruebas revisan que las descripciones tengan imagen `.webp`, que las rutas
de imagen sean relativas, y que el encabezado del padron actual se detecte.

## Publicacion

Para publicar el mapa, subir `maps-dol.html`. Si se usa la pagina contenedora,
subir tambien `index.html`.

Subir tambien la carpeta `img/` para que los popups puedan cargar las imagenes
`.webp`. El mapa necesita internet para cargar recursos externos de
Leaflet/OpenStreetMap, Bootstrap y Spotify.

## Fuentes de datos

- Padron oficial de establecimientos educativos:
  https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/padron-oficial-de-establecimientos-educativos
  https://datos.gob.ar/dataset/padron-oficial-de-establecimientos-educativos#
- CSV de nivel primario estatal usado por el script:
  https://github.com/marianof2000/datasets/raw/main/Nivel_Primario_G_Estatal.csv


Primaria 12
https://maps.app.goo.gl/bexbi8wrMq9CggYU6