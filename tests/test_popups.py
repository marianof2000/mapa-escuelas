# -*- coding: utf-8 -*-
"""Pruebas de las fichas emergentes de las escuelas."""

import unittest

from src.mapa_escuelas.config import (
    IMAGENES_POPUP_PATH,
    SPOTIFY_URL,
    URBANAS_URL,
)
from src.mapa_escuelas.popups import (
    _crear_popup_desde_html,
    _crear_popup_html,
    _imagen_popup_src,
)


class PopupsTest(unittest.TestCase):
    """Valida contenido, imagenes y seguridad basica de los popups."""

    def test_existe_imagen_webp_de_respaldo(self) -> None:
        """Verifica que exista la imagen generica de los popups.

        Precondiciones:
            La configuracion de imagenes del proyecto esta disponible.
        Postcondiciones:
            La prueba finaliza correctamente solo si existe la imagen WebP de
            respaldo; no modifica archivos.
        """
        self.assertTrue((IMAGENES_POPUP_PATH / "escuela-muestra.webp").exists())

    def test_imagen_popup_usa_ruta_webp_relativa(self) -> None:
        """Verifica la ruta relativa de una imagen propia.

        Precondiciones:
            Existe una imagen configurada para el CUE usado por la prueba.
        Postcondiciones:
            Confirma que CUE enteros y decimales equivalentes producen la
            misma ruta WebP; no modifica archivos.
        """
        self.assertEqual(_imagen_popup_src("60828200"), "img/60828200.webp")
        self.assertEqual(_imagen_popup_src("60828200.0"), "img/60828200.webp")

    def test_imagen_popup_usa_muestra_si_no_hay_foto(self) -> None:
        """Verifica el uso de la imagen de respaldo.

        Precondiciones:
            El CUE de prueba no posee imagen propia y existe la miniatura
            generica configurada.
        Postcondiciones:
            Confirma que la URL resultante referencia la imagen de muestra;
            no modifica archivos.
        """
        self.assertEqual(
            _imagen_popup_src("60200000"),
            "img/escuela-muestra.webp",
        )

    def test_imagen_popup_urbana_fuerza_imagen_generica(self) -> None:
        """Verifica la imagen generica para una escuela urbana.

        Precondiciones:
            El CUE posee una imagen propia y existe la imagen generica.
        Postcondiciones:
            Confirma que la opcion urbana ignora la foto propia y retorna la
            ruta de la imagen generica; no modifica archivos.
        """
        self.assertEqual(
            _imagen_popup_src("60827900", usar_generica=True),
            "img/escuela-muestra.webp",
        )

    def test_popup_conserva_contenido_sin_repetir_css(self) -> None:
        """Verifica contenido seguro y ausencia de estilos repetidos.

        Precondiciones:
            Los datos de escuela, enlace e historia de prueba son validos.
        Postcondiciones:
            Confirma que el popup escapa la historia, conserva enlace e
            historia y no incluye una etiqueta ``style`` propia.
        """
        html = _crear_popup_html(
            "EP 1",
            "DOMICILIO",
            "Rural",
            1,
            link="https://escuelas-dolores.example/padron_2010/1",
            historia="Historia <rural> de prueba",
        )
        popup = _crear_popup_desde_html(html)

        self.assertNotIn("<style>", html)
        self.assertIn("Abrir enlace de la escuela", html)
        self.assertIn("Historia:", html)
        self.assertIn("Historia &lt;rural&gt; de prueba", html)
        self.assertEqual(popup.options["max_width"], 600)

    def test_popup_urbano_no_muestra_historia_y_usa_recursos_comunes(self) -> None:
        """Verifica el contenido especifico de los pines celestes.

        Precondiciones:
            La URL del blog, el reproductor y la imagen generica estan
            configurados.
        Postcondiciones:
            Confirma que el popup urbano no contiene historia y que usa la
            imagen, el enlace y el reproductor comunes.
        """
        html = _crear_popup_html(
            "EP 1",
            "DOMICILIO",
            "Urbano",
            "60827900",
            link=URBANAS_URL,
            historia="Esta historia no debe mostrarse",
        )

        self.assertNotIn('class="popup-historia"', html)
        self.assertNotIn("Historia:", html)
        self.assertNotIn("Esta historia no debe mostrarse", html)
        self.assertIn('src="img/escuela-muestra.webp"', html)
        self.assertIn(f'href="{URBANAS_URL}"', html)
        self.assertIn(f'src="{SPOTIFY_URL}"', html)

    def test_popup_no_incluye_bloque_de_descripcion(self) -> None:
        """Verifica que el popup no conserve descripciones obsoletas.

        Precondiciones:
            Los datos minimos del popup son representables como texto.
        Postcondiciones:
            Confirma la ausencia del texto y de la clase de descripcion
            retirados; no modifica archivos.
        """
        html = _crear_popup_html(
            "EP 1",
            "DOMICILIO",
            "Rural",
            1,
            historia="Historia disponible",
        )

        self.assertNotIn("Descripción pendiente", html)
        self.assertNotIn('class="popup-descripcion"', html)
