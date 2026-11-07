# -*- coding: utf-8 -*-
"""Pruebas de lectura, validacion y combinacion de fuentes."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.mapa_escuelas.config import HISTORIAS_PATH, LINKS_PATH
from src.mapa_escuelas.datos import (
    _anio_para_ordenar_padron,
    _combinar_padron_con_primaria,
    _detectar_hoja_y_header_en_excel,
    _etiqueta_padron,
    _nombre_padron,
    _normalizar_cueanexo,
    cargar_escuelas_por_padron_csv,
    cargar_limite_dolores,
)
from tests.helpers import fila_padron, primaria_de_prueba


def crear_fuentes_csv(directorio: Path) -> tuple[Path, Path, Path]:
    """Crea fuentes CSV minimas y validas para pruebas de integracion.

    Precondiciones:
        ``directorio`` existe y permite escribir archivos.
    Postcondiciones:
        Crea tres CSV validos y retorna sus rutas en el orden padrones, enlaces
        e historias.
    """
    padrones_path = directorio / "padrones.csv"
    links_path = directorio / "links.csv"
    historias_path = directorio / "historias.csv"
    pd.DataFrame(
        [
            {
                "padron": "padron_2026",
                "padron_nombre": "Padrón 2026",
                "Cueanexo": 1,
                "nombre": "ESCUELA PRIMARIA Nº1",
                "latitud": -36.31,
                "longitud": -57.67,
                "Domicilio": "CALLE 1",
                "Ámbito": "Urbano",
            }
        ]
    ).to_csv(padrones_path, index=False)
    pd.DataFrame(
        [
            {
                "padron": "padron_2026",
                "Cueanexo": 1,
                "link": "https://example.test/1",
            }
        ]
    ).to_csv(links_path, index=False)
    pd.DataFrame([{"Cueanexo": 1, "historia": "Historia de prueba"}]).to_csv(
        historias_path,
        index=False,
    )
    return padrones_path, links_path, historias_path


class DatosTest(unittest.TestCase):
    """Valida esquemas, filtros, uniones y errores de las fuentes."""

    def test_detecta_header_sin_depender_de_un_xlsx_real(self) -> None:
        """Verifica la deteccion del encabezado con un libro simulado.

        Precondiciones:
            El ``DataFrame`` simulado contiene las columnas oficiales
            requeridas en su segunda fila.
        Postcondiciones:
            Confirma que se seleccionan la hoja y el indice de encabezado
            esperados sin leer un XLSX real.
        """
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
        """Verifica la extraccion del periodo desde nombres de archivo.

        Precondiciones:
            Los nombres de archivo de prueba contienen años reconocibles.
        Postcondiciones:
            Confirma que se obtienen correctamente un periodo mensual y uno
            anual; no modifica archivos.
        """
        self.assertEqual(
            _nombre_padron(Path("2026.01.12_padron_oficial.xlsx")),
            "2026.01",
        )
        self.assertEqual(
            _nombre_padron(Path("padron_oficial_de_establecimientos_2024.xlsx")),
            "2024",
        )

    def test_padron_2010_se_muestra_como_anterior_a_2011(self) -> None:
        """Verifica la etiqueta especial del padron 2010.

        Precondiciones:
            Las etiquetas recibidas son cadenas de padrones validas.
        Postcondiciones:
            Confirma que solo 2010 se presenta como ``Anterior a 2011``.
        """
        self.assertEqual(_etiqueta_padron("Padrón 2010"), "Anterior a 2011")
        self.assertEqual(_etiqueta_padron("Padrón 2011"), "Padrón 2011")

    def test_padrones_se_ordenan_desde_2026(self) -> None:
        """Verifica el orden descendente de los padrones.

        Precondiciones:
            La lista contiene etiquetas anuales compatibles con el ordenador.
        Postcondiciones:
            Confirma que 2026 aparece primero y el padron anterior a 2011 al
            final; no modifica las fuentes del proyecto.
        """
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
        """Verifica las columnas producidas al combinar un padron.

        Precondiciones:
            Los datos simulados poseen el esquema minimo de padron y primaria.
        Postcondiciones:
            Confirma que el resultado incluye identificador, nombre,
            coordenadas y domicilio; no lee archivos reales.
        """
        primaria = primaria_de_prueba()
        padron = pd.DataFrame(
            [fila_padron(60827900, "DOLORES", "DOLORES", "Estatal")]
        )
        with patch("src.mapa_escuelas.datos._cargar_padron", return_value=padron):
            escuelas = _combinar_padron_con_primaria(
                Path("padron-prueba.xlsx"),
                primaria,
            )
        for columna in ("Cueanexo", "nombre", "latitud", "longitud", "Domicilio"):
            self.assertIn(columna, escuelas.columns)

    def test_mapa_carga_capas_desde_padrones_csv(self) -> None:
        """Verifica la carga integral de capas desde los CSV versionados.

        Precondiciones:
            Los archivos de padrones, enlaces e historias existen y cumplen
            sus esquemas documentados.
        Postcondiciones:
            Confirma capas, enlaces, historias y datos de la EP 12 sin
            modificar las fuentes.
        """
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
        self.assertTrue(escuelas["historia"].eq("Historia no disponible.").any())
        self.assertTrue(HISTORIAS_PATH.exists())

    def test_combina_por_partido_y_no_solo_por_localidad(self) -> None:
        """Verifica que el filtro territorial use el partido de Dolores.

        Precondiciones:
            Los datos simulados incluyen localidades, departamentos y sectores
            diferentes.
        Postcondiciones:
            Confirma que solo permanecen escuelas estatales primarias del
            departamento Dolores.
        """
        padron = pd.DataFrame(
            [
                fila_padron(1, "DOLORES", "DOLORES", "Estatal"),
                fila_padron(2, "SEVIGNE", "DOLORES", "Estatal"),
                fila_padron(3, "DOLORES", "CASTELLI", "Estatal"),
                fila_padron(4, "DOLORES", "DOLORES", "Privado"),
                fila_padron(5, "DOLORES", "DOLORES", "Estatal", primario=" "),
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
        """Verifica la conservacion opcional de escuelas sin ubicacion.

        Precondiciones:
            El padron simulado incluye una escuela sin correspondencia en la
            fuente de coordenadas.
        Postcondiciones:
            Confirma que ambas escuelas permanecen y que la no localizada
            conserva coordenadas nulas.
        """
        padron = pd.DataFrame(
            [
                fila_padron(1, "DOLORES", "DOLORES", "Estatal"),
                fila_padron(2, "SEVIGNE", "DOLORES", "Estatal"),
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

    def test_rechaza_columnas_faltantes_en_cada_fuente(self) -> None:
        """Verifica la validacion de columnas en los tres CSV.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV de prueba.
        Postcondiciones:
            Confirma que padrones, enlaces e historias incompletos producen un
            ``ValueError`` descriptivo.
        """
        casos = (
            (0, pd.DataFrame({"padron": ["padron_2026"]})),
            (1, pd.DataFrame({"padron": ["padron_2026"]})),
            (2, pd.DataFrame({"Cueanexo": [1]})),
        )
        for indice, contenido_invalido in casos:
            with self.subTest(indice=indice), tempfile.TemporaryDirectory() as tmp:
                rutas = crear_fuentes_csv(Path(tmp))
                contenido_invalido.to_csv(rutas[indice], index=False)
                with self.assertRaisesRegex(ValueError, "Faltan columnas"):
                    cargar_escuelas_por_padron_csv(*rutas)

    def test_rechaza_enlaces_duplicados(self) -> None:
        """Verifica el rechazo de enlaces duplicados por padron y CUE.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV de prueba.
        Postcondiciones:
            Confirma que dos enlaces con la misma clave producen
            ``ValueError``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            padrones_path, links_path, historias_path = crear_fuentes_csv(Path(tmp))
            enlace = {
                "padron": "padron_2026",
                "Cueanexo": 1,
                "link": "https://example.test/1",
            }
            pd.DataFrame([enlace, enlace]).to_csv(links_path, index=False)
            with self.assertRaisesRegex(ValueError, "enlaces duplicados"):
                cargar_escuelas_por_padron_csv(
                    padrones_path,
                    links_path,
                    historias_path,
                )

    def test_rechaza_historias_duplicadas(self) -> None:
        """Verifica el rechazo de historias duplicadas por CUE.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV de prueba.
        Postcondiciones:
            Confirma que dos historias para el mismo CUE producen
            ``ValueError``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            padrones_path, links_path, historias_path = crear_fuentes_csv(Path(tmp))
            pd.DataFrame(
                [
                    {"Cueanexo": 1, "historia": "Primera"},
                    {"Cueanexo": 1, "historia": "Segunda"},
                ]
            ).to_csv(historias_path, index=False)
            with self.assertRaisesRegex(ValueError, "historias duplicadas"):
                cargar_escuelas_por_padron_csv(
                    padrones_path,
                    links_path,
                    historias_path,
                )

    def test_rechaza_geojson_malformado(self) -> None:
        """Verifica el rechazo de un GeoJSON sintacticamente invalido.

        Precondiciones:
            Se puede escribir un archivo temporal con JSON malformado.
        Postcondiciones:
            Confirma que la carga propaga ``JSONDecodeError`` y no produce un
            limite parcial.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "limite.geojson"
            path.write_text("{geojson invalido", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                cargar_limite_dolores(path)

    def test_rechaza_geojson_sin_dolores(self) -> None:
        """Verifica el rechazo de un GeoJSON sin el partido buscado.

        Precondiciones:
            Se puede escribir un GeoJSON temporal con una feature valida.
        Postcondiciones:
            Confirma que la ausencia de Dolores produce ``ValueError``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "limite.geojson"
            contenido = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"fna": "Castelli"},
                        "geometry": None,
                    }
                ],
            }
            path.write_text(json.dumps(contenido), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Dolores"):
                cargar_limite_dolores(path)
