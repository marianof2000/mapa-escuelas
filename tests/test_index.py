# -*- coding: utf-8 -*-
"""Pruebas de la pagina contenedora del mapa."""

from pathlib import Path
import unittest


INDEX_PATH = Path(__file__).resolve().parents[1] / "index.html"


class IndexHtmlTest(unittest.TestCase):
    """Valida la estructura principal de la pagina contenedora."""

    def test_franja_lateral_y_footer_tienen_colores_diferenciados(self) -> None:
        """Verifica el ancho y los colores de la franja y el footer.

        Precondiciones:
            ``index.html`` existe y contiene sus estilos dentro del documento.
        Postcondiciones:
            Confirma que la franja es un ``aside`` de un sexto del ancho y que
            el footer usa un fondo un cinco por ciento mas oscuro.
        """
        html = INDEX_PATH.read_text(encoding="utf-8")

        self.assertIn('<aside class="text-strip"', html)
        self.assertIn("flex: 0 0 16.666667%;", html)
        self.assertIn("width: 16.666667%;", html)
        self.assertIn("background-color: #f8f9fa85;", html)
        self.assertIn("--footer-background: #ecedee;", html)
        self.assertEqual(
            html.count("background-color: var(--footer-background);"),
            1,
        )

    def test_enlace_al_blog_aparece_debajo_del_texto(self) -> None:
        """Verifica el enlace independiente al blog del proyecto.

        Precondiciones:
            ``index.html`` existe y contiene la franja informativa.
        Postcondiciones:
            Confirma que el párrafo queda como texto y que debajo aparece un
            enlace seguro al blog, abierto en una pestaña nueva.
        """
        html = INDEX_PATH.read_text(encoding="utf-8")

        paragraph_end = html.index("</p>")
        link_start = html.index('<a\n        class="text-strip-link"')

        self.assertLess(paragraph_end, link_start)
        self.assertIn(
            'href="https://voces-rurales-dolores.blogspot.com/"',
            html,
        )
        self.assertIn("Voces Rurales Dolores", html)
        self.assertIn('class="text-strip-link"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertNotIn("<href>", html)

    def test_unq_enlaza_a_la_pagina_de_la_maestria(self) -> None:
        """Verifica el enlace institucional incluido en el párrafo.

        Precondiciones:
            ``index.html`` contiene la referencia textual a la UNQ.
        Postcondiciones:
            Confirma que únicamente la sigla visible enlaza de forma segura a
            la página de la Maestría en Historia Pública de la UNQ.
        """
        html = INDEX_PATH.read_text(encoding="utf-8")
        unq_url = (
            "https://www.unq.edu.ar/carrera/"
            "110-maestria-en-historia-publica-y-divulgacion-de-la-historia/"
        )

        self.assertIn(f'href="{unq_url}"', html)
        self.assertIn(">UNQ</a>", html)
        self.assertEqual(html.count(f'href="{unq_url}"'), 1)
