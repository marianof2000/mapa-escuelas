# -*- coding: utf-8 -*-
"""Validaciones basicas del proyecto sin depender de internet."""

import json
from pathlib import Path
import unittest

from src.mapa_escuelas.config import DESCRIPCIONES_PATH, IMAGENES_POPUP_PATH, PADRON_PATH
from src.mapa_escuelas.funciones import (
    _combinar_padron_con_primaria,
    _detectar_hoja_y_header_padron,
    _imagen_popup_src,
    _nombre_padron,
    cargar_escuelas_por_padron_csv,
)


class ValidacionProyectoTest(unittest.TestCase):
    def test_descripciones_tienen_imagen_webp(self) -> None:
        descripciones = json.loads(DESCRIPCIONES_PATH.read_text(encoding="utf-8"))
        imagenes = {path.stem for path in IMAGENES_POPUP_PATH.glob("*.webp")}
        self.assertFalse(sorted(set(descripciones) - imagenes))

    def test_imagen_popup_usa_ruta_webp_relativa(self) -> None:
        self.assertEqual(_imagen_popup_src("60828200"), "img/60828200.webp")

    def test_detecta_header_padron_actual(self) -> None:
        hoja, header = _detectar_hoja_y_header_padron(PADRON_PATH)
        self.assertTrue(hoja)
        self.assertIsInstance(header, int)

    def test_nombre_padron_extrae_anio(self) -> None:
        self.assertEqual(
            _nombre_padron(Path("2026.01.12_padron_oficial.xlsx")),
            "2026.01",
        )
        self.assertEqual(
            _nombre_padron(Path("padron_oficial_de_establecimientos_2024.xlsx")),
            "2024",
        )

    def test_csv_de_padron_incluye_columnas_para_mapa(self) -> None:
        primaria = _primaria_de_prueba()
        escuelas = _combinar_padron_con_primaria(PADRON_PATH, primaria)
        for columna in ("Cueanexo", "nombre", "latitud", "longitud", "Domicilio"):
            self.assertIn(columna, escuelas.columns)

    def test_mapa_carga_capas_desde_padrones_csv(self) -> None:
        capas = cargar_escuelas_por_padron_csv()
        self.assertTrue(capas)
        for escuelas in capas.values():
            for columna in ("Cueanexo", "nombre", "latitud", "longitud"):
                self.assertIn(columna, escuelas.columns)


def _primaria_de_prueba():
    import pandas as pd

    return pd.DataFrame(
        [
            {
                "Cueanexo": 60827900,
                "nombre": 'ESCUELA DE EDUCACIÓN PRIMARIA Nº1 "PEDRO CASTELLI"',
                "id_modalidad": 1,
                "modalidad": "Común",
                "id_nivel": 2,
                "nivel": "Primario",
                "id_periodo": 1,
                "periodo": "Común",
                "calle": "MARQUEZ",
                "nro": "",
                "localidad": "DOLORES",
                "codigo_postal": "",
                "nro_escuela": 1,
                "latitud": -36.31,
                "longitud": -57.67,
            }
        ]
    )


if __name__ == "__main__":
    unittest.main()
