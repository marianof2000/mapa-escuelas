# -*- coding: utf-8 -*-
"""Constructores de datos compartidos por las pruebas."""

import pandas as pd


def primaria_de_prueba() -> pd.DataFrame:
    """Construye una fuente primaria minima para las pruebas.

    Precondiciones:
        pandas esta disponible y admite construir un ``DataFrame``.
    Postcondiciones:
        Retorna un nuevo ``DataFrame`` de una escuela con las columnas
        utilizadas por las pruebas; no modifica archivos.
    """
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


def fila_padron(
    cueanexo: int,
    localidad: str,
    departamento: str,
    sector: str,
    primario: object = 1,
) -> dict[str, object]:
    """Construye una fila de padron configurable para las pruebas.

    Precondiciones:
        Los argumentos representan valores admitidos por un padron oficial de
        prueba y ``cueanexo`` es entero.
    Postcondiciones:
        Retorna un nuevo diccionario con el esquema minimo del padron; no
        modifica los argumentos.
    """
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
