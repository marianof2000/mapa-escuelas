# Anexo técnico: desarrollo de un mapa histórico de escuelas primarias de Dolores

## 1. Introducción

El presente anexo describe y fundamenta el desarrollo de una herramienta
informática destinada a organizar, relacionar y visualizar información
histórica sobre las escuelas primarias estatales del partido de Dolores,
provincia de Buenos Aires. El trabajo surgió de la necesidad de consultar, en
un mismo entorno, padrones educativos correspondientes a distintos años y de
representar territorialmente la evolución de los establecimientos.

Los padrones oficiales constituyen una fuente relevante para el estudio del
sistema educativo, pero presentan dificultades para su análisis longitudinal.
Se distribuyen como libros de cálculo independientes, sus encabezados y
estructuras pueden variar entre períodos y no siempre contienen coordenadas
completas. Además, la información descriptiva, los enlaces, las imágenes y las
historias institucionales se encuentran en fuentes separadas. Estas
características hacen necesaria una etapa previa de normalización e integración
antes de construir cualquier visualización.

Como respuesta a este problema se desarrolló una aplicación reproducible en
Python que transforma los padrones XLSX en un conjunto de datos consolidado y,
a partir de él, genera un mapa web interactivo. El producto final es el archivo
`maps-dol.html`, que puede consultarse directamente en un navegador o
incorporarse dentro de otra página mediante `index.html`.

## 2. Objetivos del desarrollo

### 2.1. Objetivo general

Construir una herramienta que permita integrar y representar geográficamente
los padrones históricos de escuelas primarias estatales del partido de Dolores,
facilitando su consulta temporal, territorial e institucional.

### 2.2. Objetivos específicos

- Automatizar la lectura de padrones oficiales almacenados en formato XLSX.
- Identificar y conservar únicamente los establecimientos primarios, estatales
  y pertenecientes al partido de Dolores.
- Unificar los registros correspondientes al período 2010-2026.
- Normalizar identificadores, nombres, domicilios y coordenadas.
- Recuperar coordenadas faltantes mediante reglas explícitas y verificables.
- Relacionar los establecimientos con historias, enlaces e imágenes.
- Permitir la consulta de un padrón por vez y la búsqueda de una escuela a lo
  largo de los diferentes períodos.
- Diferenciar visualmente las escuelas rurales de las urbanas.
- Producir un archivo HTML autónomo, publicable y de tamaño reducido.
- Incorporar pruebas automatizadas que controlen la integridad de los datos y
  el comportamiento del sistema.

## 3. Alcance

El alcance territorial se limita al partido de Dolores. El alcance
institucional comprende escuelas primarias de gestión estatal. El alcance
temporal abarca los padrones disponibles desde 2010 hasta 2026.

La herramienta no reemplaza al padrón oficial ni pretende constituir una
fuente administrativa. Su finalidad es facilitar la exploración y el análisis
de información previamente publicada, complementada con datos históricos y
geográficos. Cuando una coordenada no se encuentra en un padrón antiguo, el
sistema aplica reglas documentadas para reutilizar la ubicación más reciente
disponible. Por este motivo, una coordenada representada en un período
histórico puede corresponder a una reconstrucción basada en otra fuente y no a
una medición realizada específicamente en ese año.

## 4. Fuentes de información

El sistema combina las siguientes fuentes:

- padrones oficiales de establecimientos educativos en formato XLSX;
- un conjunto de escuelas primarias utilizado para complementar nombres y
  coordenadas;
- `data/padrones.csv`, resultado consolidado de la conversión;
- `data/links.csv`, con un enlace y un nombre de referencia por `Cueanexo`;
- `data/indice_escuelas_rurales_dolores_CUE.csv`, que contiene historias
  institucionales asociadas mediante CUE;
- `data/limite_partidos.geojson`, utilizado para representar el límite del
  partido de Dolores;
- imágenes de las escuelas en formato WebP;
- coordenadas oficiales incorporadas manualmente para casos puntuales cuya
  ubicación fue verificada de manera independiente.

El identificador `Cueanexo` funciona como clave principal para relacionar las
fuentes. Antes de efectuar las uniones, el código normaliza su representación
para evitar que un mismo identificador sea interpretado como diferente por
estar almacenado como número entero, decimal o cadena de texto.

## 5. Metodología de procesamiento

El trabajo se organizó como un flujo de extracción, transformación e
integración de datos. Se separaron dos procesos: la conversión de los padrones
y la generación del mapa.

### 5.1. Lectura de los libros XLSX

Los libros se procesan con pandas mediante el motor Calamine. Como la hoja y la
fila de encabezados pueden variar, el sistema inspecciona las primeras filas de
cada hoja hasta encontrar el conjunto de columnas obligatorias. De esta manera,
la conversión no depende de que todos los archivos mantengan exactamente la
misma disposición visual.

Una vez localizado el encabezado, los nombres de las columnas se normalizan y
se aplican los siguientes filtros:

1. jurisdicción igual a Buenos Aires;
2. sector estatal;
3. nivel primario activo;
4. departamento igual a Dolores.

El filtro territorial se realiza mediante el campo correspondiente al partido
o departamento y no únicamente mediante la localidad. Esta decisión permite
conservar establecimientos situados en localidades rurales pertenecientes a
Dolores y excluir localidades homónimas de otros partidos.

### 5.2. Consolidación de períodos

Cada padrón filtrado recibe un identificador estable, una etiqueta visible y
la referencia al archivo de origen. Los resultados se concatenan en
`data/padrones.csv`. El padrón de 2010 se presenta en la interfaz con la
leyenda `Anterior a 2011`, dado que incluye información histórica previa al
conjunto regular de padrones posteriores.

El nombre visible de los establecimientos se obtiene de las columnas `nombre`
o `Nombre`. El sistema prioriza `nombre` y utiliza `Nombre` cuando la primera
no existe o se encuentra vacía. Luego genera una columna canónica denominada
`nombre`, que es la utilizada por los marcadores, los resultados de búsqueda y
las fichas emergentes. Si ninguna de las dos fuentes contiene una denominación,
la generación se interrumpe para evitar pines sin identificar.

### 5.3. Recuperación de coordenadas

Para completar ubicaciones faltantes se definió una estrategia jerárquica:

1. **Coordenadas oficiales configuradas:** tienen prioridad para los casos
   verificados manualmente.
2. **Coordenadas del mismo CUE:** se reutiliza el par más reciente disponible
   para el mismo `Cueanexo`.
3. **Coincidencia territorial:** cuando no existe una ubicación por CUE, se
   busca la coincidencia más reciente de departamento, localidad y domicilio.

Las coordenadas se utilizan siempre como pares completos de latitud y longitud.
Si después de aplicar las tres estrategias queda una escuela sin ubicación, la
conversión finaliza con un error que identifica los CUE afectados. Esta
decisión evita generar marcadores parciales o ubicaciones silenciosamente
incorrectas.

### 5.4. Integración de enlaces e historias

El archivo `data/links.csv` contiene una sola fila por `Cueanexo` y las
columnas `Cueanexo`, `link` y `Nombre`. La columna `Nombre` facilita la lectura
y revisión manual del CSV, mientras que la unión automática utiliza únicamente
el CUE. De este modo, el mismo enlace se reutiliza en todos los años donde
aparece la escuela sin duplicar información por padrón.

El sistema verifica que no existan CUE repetidos, enlaces vacíos ni nombres de
referencia faltantes. Las historias también se relacionan mediante CUE. Cuando
una escuela no posee historia disponible, se incorpora una leyenda explícita en
lugar de dejar un valor nulo.

### 5.5. Tratamiento del límite geográfico

El límite del partido se almacena en GeoJSON. Durante la carga se valida la
estructura y se selecciona la entidad cuya denominación corresponde a Dolores.
La generación se interrumpe si el archivo es inválido o si no contiene el
partido buscado. El límite resultante se incorpora como una capa geográfica que
permite interpretar los puntos dentro de su contexto territorial.

## 6. Diseño y arquitectura del software

El código se organizó en módulos con responsabilidades diferenciadas:

- `config.py` centraliza rutas, URLs, columnas obligatorias y coordenadas
  oficiales;
- `datos.py` carga, normaliza, valida y relaciona las fuentes;
- `convertir.py` transforma los XLSX en `padrones.csv` y aplica las estrategias
  de coordenadas;
- `popups.py` construye las fichas emergentes y escapa el contenido proveniente
  de los datos;
- `controles.py` genera los marcadores, las capas, el selector, el resumen y el
  buscador;
- `plantillas.py` carga y conserva en caché los recursos de interfaz;
- `mapa.py` compone el objeto cartográfico y conecta sus componentes;
- `generar_mapa.py` coordina la carga, la construcción, el guardado y la
  compactación del HTML;
- `templates/` contiene el CSS y las plantillas JavaScript/Jinja;
- `tests/` reúne las pruebas automatizadas separadas por responsabilidad.

Esta separación reduce el acoplamiento entre la preparación de datos y la
presentación. También permite modificar una regla de coordenadas, una ficha o
un control sin intervenir el resto del proceso.

Todas las funciones Python declaran anotaciones de tipos y documentan
contratos mediante precondiciones y postcondiciones. Una prueba analiza el
código con el módulo `ast` y falla si encuentra una función sin firma tipada o
sin ambas secciones contractuales.

## 7. Construcción del mapa interactivo

Para cada padrón se crea una capa independiente de marcadores. Solo una capa se
presenta como activa, lo que permite comparar períodos sin superponer todos los
puntos al mismo tiempo. Los padrones se ordenan de forma descendente y 2026 se
selecciona por defecto.

Los marcadores se agrupan mediante `MarkerCluster`. Se utiliza una codificación
cromática para distinguir escuelas rurales y urbanas. El resumen del período
activo contabiliza ambos ámbitos y se actualiza al cambiar de padrón.

El buscador indexa nombre, CUE, domicilio, localidad y otros campos disponibles.
Cuando el usuario selecciona un resultado perteneciente a otro año, la
aplicación activa automáticamente la capa correspondiente y abre la ficha del
marcador.

Cada ficha emergente puede mostrar:

- denominación de la escuela;
- domicilio y ámbito;
- historia institucional;
- enlace externo;
- imagen específica identificada por CUE;
- imagen genérica cuando no existe una fotografía propia;
- reproductor de audio incorporado mediante Spotify.

El mapa incluye además el límite de Dolores, una base cartográfica de
OpenStreetMap, un minimapa, escala gráfica y un visor de coordenadas.

## 8. Optimización del archivo generado

Una primera mejora consistió en trasladar el CSS de las fichas a una plantilla
global. En lugar de repetir los mismos estilos dentro de cada marcador, el CSS
se inserta una única vez en el encabezado del documento.

Posteriormente se incorporó una compactación automática. Después de que Folium
guarda el mapa, el sistema elimina líneas vacías e indentación inicial que no
poseen significado visual. Esta operación no retira marcadores, historias ni
controles.

En la versión evaluada, el archivo pasó de 1.557.555 a 1.407.785 bytes, una
reducción aproximada del 9,6 %. El resultado quedó por debajo del objetivo de
1,5 MB y conservó los 358 marcadores y sus correspondientes fichas. Si el
servidor web utiliza compresión HTTP, el volumen transferido puede reducirse
aún más.

## 9. Tecnologías empleadas y justificación

- **Python 3.12:** lenguaje principal, elegido por su ecosistema de análisis de
  datos y su legibilidad.
- **pandas:** permite leer, filtrar, transformar, agrupar y unir datos
  tabulares de forma reproducible.
- **python-calamine:** motor de lectura de XLSX utilizado por pandas; evita
  depender de la automatización de una aplicación de escritorio.
- **Folium:** genera mapas web sobre Leaflet a partir de objetos Python.
- **Branca:** aporta plantillas y elementos HTML compatibles con Folium.
- **Leaflet:** proporciona la interacción cartográfica en el navegador.
- **OpenStreetMap:** funciona como cartografía base.
- **GeoJSON:** formato interoperable utilizado para el límite territorial.
- **HTML, CSS y JavaScript:** implementan la presentación y la interacción del
  producto final.
- **Jinja:** permite generar controles JavaScript a partir de los datos y de
  los nombres internos creados por Folium.
- **CSV y XLSX:** se utilizan como formatos de entrada, intercambio y
  consolidación.
- **WebP:** reduce el peso de las imágenes manteniendo una calidad adecuada
  para las miniaturas.
- **Spotify Embed:** integra contenido sonoro dentro de las fichas.
- **pytest:** ejecuta las pruebas automatizadas y facilita la identificación de
  regresiones.
- **uv:** resuelve dependencias, sincroniza el entorno y ejecuta los comandos
  del proyecto.
- **setuptools:** construye el paquete distribuible e incorpora las plantillas
  CSS y Jinja.

## 10. Estrategia de validación

La validación se realiza mediante pruebas automatizadas separadas por módulo.
Entre otros aspectos, se comprueba:

- detección de hojas y encabezados en los XLSX;
- filtrado por nivel, sector y partido;
- extracción y ordenamiento de períodos;
- normalización de `Cueanexo` y del nombre de las escuelas;
- columnas obligatorias en cada fuente;
- rechazo de enlaces e historias duplicados;
- rechazo de GeoJSON malformado o sin Dolores;
- uso de coordenadas oficiales y recuperación histórica de ubicaciones;
- rechazo de escuelas que no pueden localizarse;
- construcción segura de las fichas;
- presencia del selector, buscador y resumen rural/urbano;
- carga única del CSS compartido;
- compactación del HTML;
- cumplimiento de type hints y contratos pre/post.

Al momento de redactar este anexo, la suite contiene 28 pruebas y 5 subpruebas.
Además de las pruebas, se valida la sintaxis del JavaScript generado, la
presencia de los 358 marcadores y la inclusión del CSS y las plantillas dentro
del paquete distribuible.

## 11. Reproducibilidad

El entorno se define en `pyproject.toml` y `uv.lock`. Las dependencias pueden
sincronizarse con:

```bash
uv sync
```

La conversión de los padrones se ejecuta con:

```bash
uv run mapa-escuelas-convertir
```

La generación del mapa se ejecuta con:

```bash
uv run mapa-escuelas-generar
```

Las pruebas se ejecutan con:

```bash
uv run pytest -q
```

La separación entre fuentes, transformación y presentación permite regenerar
el producto cuando se incorpora un nuevo padrón o se corrige una fuente, sin
editar manualmente el HTML.

## 12. Limitaciones y criterios de interpretación

- La precisión histórica depende de la calidad y disponibilidad de los
  padrones originales.
- Algunas coordenadas antiguas se reconstruyen a partir de información más
  reciente o de coincidencias de domicilio.
- La ausencia de una historia institucional no implica que la escuela carezca
  de antecedentes, sino que no existe un texto asociado en la fuente utilizada.
- Las imágenes y los enlaces funcionan como recursos complementarios y no como
  evidencia administrativa.
- La visualización necesita acceso a internet para cargar la cartografía base,
  las bibliotecas web y el reproductor externo.
- El mapa representa establecimientos presentes en las fuentes procesadas; no
  debe interpretarse como una certificación oficial de funcionamiento actual.

## 13. Resultados y conclusión

El desarrollo permitió convertir un conjunto heterogéneo de padrones anuales
en una herramienta de consulta histórica y territorial. El proceso automatiza
la selección de escuelas de Dolores, normaliza claves y nombres, recupera
coordenadas faltantes, vincula información complementaria y produce una
interfaz navegable por período.

La modularización del código, los contratos, los type hints y las pruebas
automatizadas aportan trazabilidad y reducen el riesgo de introducir errores
al actualizar las fuentes. La compactación del archivo final mejora su
publicación sin sacrificar contenido. En conjunto, la solución constituye un
procedimiento reproducible para preservar, relacionar y comunicar información
educativa histórica mediante una representación cartográfica interactiva.
