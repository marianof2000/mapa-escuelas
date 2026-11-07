# -*- coding: utf-8 -*-
"""Pruebas del guardado compacto del mapa generado."""

from pathlib import Path
import tempfile
import unittest

import folium

from src.mapa_escuelas.generar_mapa import (
    _compactar_html_generado,
    _guardar_mapa_compacto,
)


class GenerarMapaTest(unittest.TestCase):
    """Valida la compactacion y escritura del HTML final."""

    def test_compacta_lineas_vacias_e_indentacion(self) -> None:
        """Verifica la transformacion determinista del HTML.

        Precondiciones:
            La muestra contiene lineas vacias y contenido indentado.
        Postcondiciones:
            Confirma que se eliminan espacios iniciales y lineas vacias sin
            alterar el contenido restante.
        """
        html = "<html>\n    <body>\n\n        <p>Mapa</p>\n    </body>\n</html>\n"

        resultado = _compactar_html_generado(html)

        self.assertEqual(
            resultado,
            "<html>\n<body>\n<p>Mapa</p>\n</body>\n</html>\n",
        )

    def test_guarda_un_mapa_compacto(self) -> None:
        """Verifica la escritura compactada de un mapa Folium real.

        Precondiciones:
            Se puede crear un archivo temporal y Folium puede renderizar un
            mapa basico.
        Postcondiciones:
            Confirma que el archivo existe, conserva el mapa y no contiene
            lineas vacias ni lineas con indentacion inicial.
        """
        mapa = folium.Map(location=[-36.31, -57.67], zoom_start=10)
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "mapa.html"

            _guardar_mapa_compacto(mapa, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertIn(mapa.get_name(), html)
            self.assertFalse(any(not linea.strip() for linea in html.splitlines()))
            self.assertFalse(
                any(linea.startswith((" ", "\t")) for linea in html.splitlines())
            )
