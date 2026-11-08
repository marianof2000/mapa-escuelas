# -*- coding: utf-8 -*-
"""Pruebas de las estrategias para completar coordenadas."""

import unittest

import pandas as pd

from src.mapa_escuelas.convertir import _completar_coordenadas_mas_recientes


class ConvertirTest(unittest.TestCase):
    """Valida la consolidacion de coordenadas historicas y oficiales."""

    def test_completa_coordenadas_con_el_dato_mas_reciente(self) -> None:
        """Verifica las estrategias historicas para completar coordenadas.

        Precondiciones:
            El conjunto simulado esta ordenado cronologicamente y contiene
            coordenadas recientes por CUE o domicilio.
        Postcondiciones:
            Confirma que se completan todas las ubicaciones con los pares mas
            recientes aplicables sin alterar las coordenadas existentes.
        """
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
        """Verifica el rechazo de escuelas imposibles de localizar.

        Precondiciones:
            El conjunto simulado no contiene coordenadas ni coincidencias
            utilizables para el CUE de prueba.
        Postcondiciones:
            Confirma que se lanza ``ValueError`` mencionando el CUE faltante.
        """
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
        """Verifica las coordenadas oficiales de la escuela 27.

        Precondiciones:
            La configuracion contiene coordenadas oficiales para el CUE
            60828000.
        Postcondiciones:
            Confirma que el resultado utiliza exactamente el par configurado.
        """
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
        """Verifica las coordenadas oficiales de la escuela 12.

        Precondiciones:
            La configuracion contiene coordenadas oficiales para el CUE
            60200000.
        Postcondiciones:
            Confirma que el resultado utiliza exactamente el par configurado.
        """
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

    def test_usa_coordenadas_oficiales_para_escuela_7(self) -> None:
        """Verifica las coordenadas oficiales de la escuela 7.

        Precondiciones:
            La configuracion contiene coordenadas oficiales para el CUE
            60250800.
        Postcondiciones:
            Confirma que el resultado reemplaza cualquier valor previo por el
            par oficial configurado.
        """
        padrones = pd.DataFrame(
            [
                {
                    "Cueanexo": 60250800,
                    "Departamento": "DOLORES",
                    "Localidad": "DOLORES",
                    "Domicilio": "BUENOS AIRES 1280",
                    "latitud": -36.29887901,
                    "longitud": -57.68754443,
                }
            ]
        )

        resultado = _completar_coordenadas_mas_recientes(padrones)

        self.assertEqual(resultado.iloc[0]["latitud"], -36.3046637)
        self.assertEqual(resultado.iloc[0]["longitud"], -57.6839118)
