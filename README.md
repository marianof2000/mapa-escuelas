# Mapa de escuelas primarias de Dolores

Este proyecto genera el archivo `maps-dol.html`, un mapa interactivo hecho con
Folium para publicar en la web.

## Uso

1. Instalar dependencias:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Verificar que existan los datos fuente en la raiz del proyecto:

   - `2023.09.04_padron_oficial_establecimientos_educativos_die.xlsx`
   - `limite_partidos.geojson`

3. Generar el HTML:

   ```bash
   python3 mapas_escuelas_dolores_taller_producción_de_obra_vero.py
   ```

El resultado se guarda en `maps-dol.html`.

## Publicacion

Subir `maps-dol.html` al servidor web junto con acceso a internet para que
Leaflet, OpenStreetMap, Bootstrap y Spotify carguen sus recursos externos.
