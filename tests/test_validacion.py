# -*- coding: utf-8 -*-
"""Validaciones basicas del proyecto sin depender de internet."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from src.mapa_escuelas.config import (
    HISTORIAS_PATH,
    IMAGENES_POPUP_PATH,
    LINKS_PATH,
)
from src.mapa_escuelas.convertir import _completar_coordenadas_mas_recientes
from src.mapa_escuelas.datos import (
    _combinar_padron_con_primaria,
    _detectar_hoja_y_header_en_excel,
    _etiqueta_padron,
    _anio_para_ordenar_padron,
    _normalizar_cueanexo,
    _nombre_padron,
    cargar_escuelas_por_padron_csv,
)
from src.mapa_escuelas.mapa import crear_mapa
from src.mapa_escuelas.popups import (
    _crear_popup_desde_html,
    _crear_popup_html,
    _imagen_popup_src,
)


class ValidacionProyectoTest(unittest.TestCase):
    def test_existe_imagen_webp_de_respaldo(self) -> None:
        self.assertTrue((IMAGENES_POPUP_PATH / "escuela-muestra.webp").exists())

    def test_imagen_popup_usa_ruta_webp_relativa(self) -> None:
        self.assertEqual(_imagen_popup_src("60828200"), "img/60828200.webp")
        self.assertEqual(_imagen_popup_src("60828200.0"), "img/60828200.webp")

    def test_imagen_popup_usa_muestra_si_no_hay_foto(self) -> None:
        self.assertEqual(
            _imagen_popup_src("60200000"),
            "img/escuela-muestra.webp",
        )

    def test_popup_es_mas_ancho_y_adaptable(self) -> None:
        html = _crear_popup_html(
            "EP 1",
            "DOMICILIO",
            "Urbano",
            1,
            link="https://escuelas-dolores.example/padron_2010/1",
            historia="Historia <rural> de prueba",
        )
        popup = _crear_popup_desde_html(html)

        self.assertIn("width: 560px", html)
        self.assertIn("max-width: calc(100vw - 80px)", html)
        self.assertIn("Abrir enlace de la escuela", html)
        self.assertIn("Historia:", html)
        self.assertIn("Historia &lt;rural&gt; de prueba", html)
        self.assertEqual(popup.options["max_width"], 600)

    def test_popup_no_incluye_bloque_de_descripcion(self) -> None:
        html = _crear_popup_html(
            "EP 1",
            "DOMICILIO",
            "Rural",
            1,
            historia="Historia disponible",
        )

        self.assertNotIn("Descripción pendiente", html)
        self.assertNotIn('class="popup-descripcion"', html)

    def test_detecta_header_sin_depender_de_un_xlsx_real(self) -> None:
        excel = type("ExcelDePrueba", (), {"sheet_names": ["Padron"]})()
        encabezados = [
            "Cueanexo",
            "Jurisdicción",
            "Sector",
            "Primario",
            "Localidad",
            "Departamento",
            "Mail",
        ]
        preview = pd.DataFrame(
            [["Padrón oficial", *([None] * 6)], encabezados]
        )

        with patch("src.mapa_escuelas.datos.pd.read_excel", return_value=preview):
            hoja, header = _detectar_hoja_y_header_en_excel(
                excel,
                Path("padron-prueba.xlsx"),
            )

        self.assertEqual(hoja, "Padron")
        self.assertEqual(header, 1)

    def test_nombre_padron_extrae_anio(self) -> None:
        self.assertEqual(
            _nombre_padron(Path("2026.01.12_padron_oficial.xlsx")),
            "2026.01",
        )
        self.assertEqual(
            _nombre_padron(Path("padron_oficial_de_establecimientos_2024.xlsx")),
            "2024",
        )

    def test_padron_2010_se_muestra_como_anterior_a_2011(self) -> None:
        self.assertEqual(_etiqueta_padron("Padrón 2010"), "Anterior a 2011")
        self.assertEqual(_etiqueta_padron("Padrón 2011"), "Padrón 2011")

    def test_padrones_se_ordenan_desde_2026(self) -> None:
        nombres = ["Anterior a 2011", "Padrón 2011", "Padrón 2026"]

        ordenados = sorted(
            nombres,
            key=_anio_para_ordenar_padron,
            reverse=True,
        )

        self.assertEqual(
            ordenados,
            ["Padrón 2026", "Padrón 2011", "Anterior a 2011"],
        )

    def test_csv_de_padron_incluye_columnas_para_mapa(self) -> None:
        primaria = _primaria_de_prueba()
        padron = pd.DataFrame(
            [_fila_padron(60827900, "DOLORES", "DOLORES", "Estatal")]
        )
        with patch("src.mapa_escuelas.datos._cargar_padron", return_value=padron):
            escuelas = _combinar_padron_con_primaria(
                Path("padron-prueba.xlsx"),
                primaria,
            )
        for columna in ("Cueanexo", "nombre", "latitud", "longitud", "Domicilio"):
            self.assertIn(columna, escuelas.columns)

    def test_mapa_carga_capas_desde_padrones_csv(self) -> None:
        capas = cargar_escuelas_por_padron_csv()
        self.assertTrue(capas)
        self.assertIn("Anterior a 2011", capas)
        self.assertNotIn("Padrón 2010", capas)
        cantidad_links = sum(len(escuelas) for escuelas in capas.values())
        self.assertEqual(cantidad_links, len(pd.read_csv(LINKS_PATH)))
        for escuelas in capas.values():
            for columna in ("Cueanexo", "nombre", "latitud", "longitud"):
                self.assertIn(columna, escuelas.columns)
            self.assertTrue(escuelas["link"].str.startswith("https://").all())
            self.assertTrue(escuelas["historia"].str.strip().ne("").all())

        escuelas = pd.concat(capas.values(), ignore_index=True)
        ep_12 = escuelas[
            escuelas["Cueanexo"].map(_normalizar_cueanexo).eq("60200000")
        ]
        self.assertFalse(ep_12.empty)
        self.assertTrue(ep_12["historia"].str.contains("1960").all())
        self.assertTrue(
            escuelas["historia"].eq("Historia no disponible.").any()
        )
        self.assertTrue(HISTORIAS_PATH.exists())

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

        with patch("src.mapa_escuelas.datos._cargar_padron", return_value=padron):
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

        with patch("src.mapa_escuelas.datos._cargar_padron", return_value=padron):
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

    def test_usa_coordenadas_oficiales_para_escuela_12(self) -> None:
        padrones = pd.DataFrame(
            [
                {
                    "Cueanexo": 60200000,
                    "Departamento": "DOLORES",
                    "Localidad": "DOLORES",
                    "Domicilio": "RUTA 63 KM 20",
                    "latitud": None,
                    "longitud": None,
                }
            ]
        )

        resultado = _completar_coordenadas_mas_recientes(padrones)

        self.assertEqual(resultado.iloc[0]["latitud"], -36.31279)
        self.assertEqual(resultado.iloc[0]["longitud"], -57.474213)

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
        )
        html = mapa.get_root().render()

        self.assertIn("buscador-escuelas-control", html)
        self.assertIn("Buscar escuela, CUE, domicilio", html)
        self.assertIn("<select", html)
        self.assertIn('name="padron-selector"', html)
        self.assertNotIn('type="radio"', html)
        self.assertIn("padron-resumen-rurales", html)
        self.assertIn("padron-resumen-urbanas", html)
        self.assertIn("Rurales: <strong>0</strong>", html)
        self.assertIn("Urbanas: <strong>1</strong>", html)
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
        "Domicilio": "DOMICILIO DE PRUEBA",
        "Ámbito": "Urbano",
        "Mail": "escuela@example.com",
    }


if __name__ == "__main__":
    unittest.main()
