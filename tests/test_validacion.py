# -*- coding: utf-8 -*-
"""Validaciones basicas del proyecto sin depender de internet."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.mapa_escuelas.config import (
    DESCRIPCIONES_PATH,
    IMAGENES_POPUP_PATH,
    PADRON_PATH,
)
from src.mapa_escuelas.convertir import _completar_coordenadas_mas_recientes
from src.mapa_escuelas.funciones import (
    _combinar_padron_con_primaria,
    _detectar_hoja_y_header_padron,
    _imagen_popup_src,
    _nombre_padron,
    cargar_escuelas_por_padron_csv,
    crear_mapa,
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

    def test_combina_por_partido_y_no_solo_por_localidad(self) -> None:
        import pandas as pd

        padron = pd.DataFrame(
            [
                _fila_padron(1, "DOLORES", "DOLORES", "Estatal"),
                _fila_padron(2, "SEVIGNE", "DOLORES", "Estatal"),
                _fila_padron(3, "DOLORES", "CASTELLI", "Estatal"),
                _fila_padron(4, "DOLORES", "DOLORES", "Privado"),
                _fila_padron(5, "DOLORES", "DOLORES", "Estatal", primario=" "),
            ]
        )
        primaria = pd.DataFrame(
            [
                {"Cueanexo": cueanexo, "latitud": -36.0, "longitud": -57.0}
                for cueanexo in range(1, 6)
            ]
        )

        with patch("src.mapa_escuelas.funciones._cargar_padron", return_value=padron):
            escuelas = _combinar_padron_con_primaria(Path("padron.xlsx"), primaria)

        self.assertEqual(set(escuelas["Cueanexo"]), {1, 2})

    def test_conversion_puede_conservar_escuelas_sin_coordenadas(self) -> None:
        import pandas as pd

        padron = pd.DataFrame(
            [
                _fila_padron(1, "DOLORES", "DOLORES", "Estatal"),
                _fila_padron(2, "SEVIGNE", "DOLORES", "Estatal"),
            ]
        )
        primaria = pd.DataFrame(
            [{"Cueanexo": 1, "latitud": -36.0, "longitud": -57.0}]
        )

        with patch("src.mapa_escuelas.funciones._cargar_padron", return_value=padron):
            escuelas = _combinar_padron_con_primaria(
                Path("padron.xlsx"),
                primaria,
                conservar_sin_coordenadas=True,
            )

        self.assertEqual(set(escuelas["Cueanexo"]), {1, 2})
        self.assertTrue(
            escuelas.loc[escuelas["Cueanexo"] == 2, "latitud"].isna().all()
        )

    def test_completa_coordenadas_con_el_dato_mas_reciente(self) -> None:
        import pandas as pd

        padrones = pd.DataFrame(
            [
                {
                    "padron_nombre": "Padrón 2011",
                    "Cueanexo": 1,
                    "Departamento": "DOLORES",
                    "Localidad": "DOLORES",
                    "Domicilio": "CALLE 1",
                    "latitud": None,
                    "longitud": None,
                },
                {
                    "padron_nombre": "Padrón 2015",
                    "Cueanexo": 1,
                    "Departamento": "DOLORES",
                    "Localidad": "DOLORES",
                    "Domicilio": "CALLE 1",
                    "latitud": -36.1,
                    "longitud": -57.1,
                },
                {
                    "padron_nombre": "Padrón 2022",
                    "Cueanexo": 1,
                    "Departamento": "DOLORES",
                    "Localidad": "DOLORES",
                    "Domicilio": "CALLE 1",
                    "latitud": -36.2,
                    "longitud": -57.2,
                },
                {
                    "padron_nombre": "Padrón 2011",
                    "Cueanexo": 2,
                    "Departamento": "DOLORES",
                    "Localidad": "SEVIGNE",
                    "Domicilio": "CAMINO RURAL",
                    "latitud": None,
                    "longitud": None,
                },
                {
                    "padron_nombre": "Padrón 2022",
                    "Cueanexo": 3,
                    "Departamento": "DOLORES",
                    "Localidad": "SEVIGNE",
                    "Domicilio": "CAMINO RURAL",
                    "latitud": -36.3,
                    "longitud": -57.3,
                },
            ]
        )

        resultado = _completar_coordenadas_mas_recientes(padrones)

        escuela_antigua = resultado.iloc[0]
        self.assertEqual(escuela_antigua["latitud"], -36.2)
        self.assertEqual(escuela_antigua["longitud"], -57.2)
        self.assertEqual(resultado.iloc[1]["latitud"], -36.1)
        self.assertEqual(resultado.iloc[3]["latitud"], -36.3)
        self.assertEqual(resultado.iloc[3]["longitud"], -57.3)
        self.assertFalse(resultado[["latitud", "longitud"]].isna().any().any())

    def test_rechaza_escuelas_sin_ninguna_coordenada_disponible(self) -> None:
        import pandas as pd

        padrones = pd.DataFrame(
            [
                {
                    "Cueanexo": 99,
                    "Departamento": "DOLORES",
                    "Localidad": "SIN DATOS",
                    "Domicilio": "SIN DATOS",
                    "latitud": None,
                    "longitud": None,
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "99"):
            _completar_coordenadas_mas_recientes(padrones)

    def test_usa_coordenadas_oficiales_para_escuela_27(self) -> None:
        import pandas as pd

        padrones = pd.DataFrame(
            [
                {
                    "Cueanexo": 60828000,
                    "Departamento": "DOLORES",
                    "Localidad": "MONTE DEL TORDILLO",
                    "Domicilio": "CUARTEL IX MONTE DEL TORDILLO",
                    "latitud": None,
                    "longitud": None,
                }
            ]
        )

        resultado = _completar_coordenadas_mas_recientes(padrones)

        self.assertEqual(resultado.iloc[0]["latitud"], -36.4252262)
        self.assertEqual(resultado.iloc[0]["longitud"], -57.4676075)

    def test_mapa_incluye_buscador_de_escuelas(self) -> None:
        import pandas as pd

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
                }
            ]
        )
        limite = {
            "type": "FeatureCollection",
            "features": [],
        }

        mapa = crear_mapa(
            {"Padrón 2026": escuelas},
            json.dumps(limite),
            {"60827900": "Escuela histórica de Dolores"},
        )
        html = mapa.get_root().render()

        self.assertIn("buscador-escuelas-control", html)
        self.assertIn("Buscar escuela, CUE, domicilio", html)
        self.assertIn("60827900", html)
        self.assertIn("MARQUEZ 50", html)


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


def _fila_padron(
    cueanexo: int,
    localidad: str,
    departamento: str,
    sector: str,
    primario: object = 1,
) -> dict[str, object]:
    return {
        "Cueanexo": cueanexo,
        "Jurisdicción": "Buenos Aires",
        "Sector": sector,
        "Primario": primario,
        "Localidad": localidad,
        "Departamento": departamento,
        "Mail": "escuela@example.com",
    }


if __name__ == "__main__":
    unittest.main()
