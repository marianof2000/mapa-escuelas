# -*- coding: utf-8 -*-
"""Pruebas de composicion y controles del mapa Folium."""

import json
import unittest

import pandas as pd

from src.mapa_escuelas.mapa import crear_mapa


class MapaTest(unittest.TestCase):
    """Valida la interfaz generada y los estilos globales."""

    def test_mapa_incluye_controles_y_css_global_de_popups(self) -> None:
        """Verifica controles, resumen y una sola copia del CSS de popups.

        Precondiciones:
            El ``DataFrame`` simulado contiene todos los campos requeridos por
            la capa de escuelas.
        Postcondiciones:
            Confirma buscador, selector, resumen, contenido indexado y una sola
            definicion global de los estilos del popup en el HTML generado.
        """
        escuelas = pd.DataFrame(
            [
                {
                    "Cueanexo": 60827900,
                    "nombre": 'ESCUELA PRIMARIA Nº1 "PEDRO CASTELLI"',
                    "latitud": -36.31,
                    "longitud": -57.67,
                    "Domicilio": "MARQUEZ 50",
                    "Ámbito": "Urbano",
                    "Localidad": "DOLORES",
                },
                {
                    "Cueanexo": 60828200,
                    "nombre": 'ESCUELA PRIMARIA Nº4 "VICTORIANO E. MONTES"',
                    "latitud": -36.32,
                    "longitud": -57.68,
                    "Domicilio": "CALLE 4",
                    "Ámbito": "Rural",
                    "Localidad": "DOLORES",
                },
            ]
        )
        limite = {"type": "FeatureCollection", "features": []}

        mapa = crear_mapa(
            {"Padrón 2026": escuelas},
            json.dumps(limite),
        )
        html = mapa.get_root().render()

        self.assertIn("buscador-escuelas-control", html)
        self.assertIn("Buscar escuela, CUE, domicilio", html)
        self.assertIn("<select", html)
        self.assertIn('name="padron-selector"', html)
        self.assertNotIn('type="radio"', html)
        self.assertIn("Rurales: <strong>1</strong>", html)
        self.assertIn("Urbanas: <strong>1</strong>", html)
        self.assertIn("60827900", html)
        self.assertIn("MARQUEZ 50", html)
        self.assertIn("width: 560px", html)
        self.assertIn("max-width: calc(100vw - 80px)", html)
        self.assertEqual(html.count(".popup-contenido {"), 1)
