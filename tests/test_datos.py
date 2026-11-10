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
                "Cueanexo": 1,
                "link": "https://example.test/1",
                "Nombre": "ESCUELA PRIMARIA Nº1",
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
        links = pd.read_csv(LINKS_PATH, dtype=str)
        self.assertFalse(links["Cueanexo"].duplicated().any())
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

    def test_links_rurales_apuntan_a_las_publicaciones_del_blog(self) -> None:
        """Verifica los enlaces específicos de las escuelas rurales.

        Precondiciones:
            ``links.csv`` contiene un registro único por ``Cueanexo`` y las
            publicaciones rurales permanecen disponibles en el blog fuente.
        Postcondiciones:
            Confirma que cada CUE rural conserva la URL de su publicación; no
            modifica los archivos de datos.
        """
        enlaces_esperados = {
            "60251100": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-2-congreso-de.html",
            "60250900": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-6-almirante-brown-el.html",
            "60250600": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-11-sol-de-mayo.html",
            "60200000": "https://voces-rurales-dolores.blogspot.com/2026/11/la-legendaria-escuela-n-12-de-la-ruta-63.html",
            "60828200": "https://voces-rurales-dolores.blogspot.com/2026/11/la-escuela-14-dr-victoriano-e-montes.html",
            "60828100": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-16-juan-bautista.html",
            "60250300": "https://voces-rurales-dolores.blogspot.com/2026/11/la-escuela-primaria-no-17-libres-del.html",
            "60250200": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-18-hipolito-yrigoyen.html",
            "60250100": "https://voces-rurales-dolores.blogspot.com/2026/11/cuartel-ix-montes-del-tordillo-ep-19-25.html",
            "60250000": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-23-tambor-de-tacuari.html",
            "60249900": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-24-bernardino.html",
            "60249800": "https://voces-rurales-dolores.blogspot.com/2026/11/cuartel-ix-montes-del-tordillo-ep-19-25.html",
            "60828000": "https://voces-rurales-dolores.blogspot.com/2026/11/cuartel-ix-montes-del-tordillo-ep-19-25.html",
            "60251200": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-n-28-mariano-moreno.html",
            "60249700": "https://voces-rurales-dolores.blogspot.com/2026/11/escuela-primaria-rural-n-29-manuel.html",
        }
        links = pd.read_csv(LINKS_PATH, dtype=str)
        links["Cueanexo"] = links["Cueanexo"].map(_normalizar_cueanexo)
        enlaces_actuales = links.set_index("Cueanexo")["link"].to_dict()

        self.assertEqual(
            {cue: enlaces_actuales[cue] for cue in enlaces_esperados},
            enlaces_esperados,
        )

    def test_nombre_del_pin_admite_nombre_en_ambas_mayusculas(self) -> None:
        """Verifica el uso alternativo de las columnas ``nombre`` y ``Nombre``.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV validas.
        Postcondiciones:
            Confirma que ``Nombre`` se normaliza como ``nombre`` y completa los
            valores vacios de la columna en minuscula.
        """
        casos = (
            (False, "ESCUELA DESDE NOMBRE MAYUSCULA"),
            (True, "ESCUELA ALTERNATIVA"),
        )
        for conservar_minuscula, nombre_esperado in casos:
            with (
                self.subTest(conservar_minuscula=conservar_minuscula),
                tempfile.TemporaryDirectory() as tmp,
            ):
                rutas = crear_fuentes_csv(Path(tmp))
                padrones = pd.read_csv(rutas[0])
                if conservar_minuscula:
                    padrones["nombre"] = " "
                    padrones["Nombre"] = nombre_esperado
                else:
                    padrones = padrones.rename(columns={"nombre": "Nombre"})
                    padrones["Nombre"] = nombre_esperado
                padrones.to_csv(rutas[0], index=False)

                capas = cargar_escuelas_por_padron_csv(*rutas)

                escuela = capas["Padrón 2026"].iloc[0]
                self.assertEqual(escuela["nombre"], nombre_esperado)

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
            (
                0,
                pd.DataFrame(
                    {"padron": ["padron_2026"], "nombre": ["ESCUELA"]}
                ),
            ),
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
        """Verifica el rechazo de enlaces duplicados por CUE.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV de prueba.
        Postcondiciones:
            Confirma que dos enlaces con la misma clave producen
            ``ValueError``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            padrones_path, links_path, historias_path = crear_fuentes_csv(Path(tmp))
            enlace = {
                "Cueanexo": 1,
                "link": "https://example.test/1",
                "Nombre": "ESCUELA PRIMARIA Nº1",
            }
            pd.DataFrame([enlace, enlace]).to_csv(links_path, index=False)
            with self.assertRaisesRegex(ValueError, "enlaces duplicados"):
                cargar_escuelas_por_padron_csv(
                    padrones_path,
                    links_path,
                    historias_path,
                )

    def test_rechaza_nombre_vacio_en_links(self) -> None:
        """Verifica que cada enlace tenga un nombre para lectura manual.

        Precondiciones:
            Se puede crear un directorio temporal con fuentes CSV de prueba.
        Postcondiciones:
            Confirma que un ``Nombre`` vacio en ``links.csv`` produce
            ``ValueError``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            padrones_path, links_path, historias_path = crear_fuentes_csv(Path(tmp))
            pd.DataFrame(
                [{"Cueanexo": 1, "link": "https://example.test/1", "Nombre": ""}]
            ).to_csv(links_path, index=False)
            with self.assertRaisesRegex(ValueError, "Faltan nombres"):
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
