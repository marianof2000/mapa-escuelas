# -*- coding: utf-8 -*-
"""Convierte los padrones XLSX en un CSV unico listo para el mapa."""

import argparse
import logging
from pathlib import Path
import re

import pandas as pd

from .config import (
    COORDENADAS_OFICIALES,
    PADRONES_CSV_PATH,
    PADRONES_DIR,
    PRIMARIA_URL,
)
from .funciones import (
    _cargar_primaria,
    _combinar_padron_con_primaria,
    _etiqueta_padron,
    _nombre_padron,
    listar_padrones,
)


LOGGER = logging.getLogger(__name__)


def convertir_padrones(
    padrones_dir: Path = PADRONES_DIR,
    output_path: Path = PADRONES_CSV_PATH,
    primaria_url: str = PRIMARIA_URL,
) -> pd.DataFrame:
    """Consolida en un CSV todos los padrones XLSX validos de un directorio.

    Precondiciones:
        ``padrones_dir`` es accesible, ``primaria_url`` identifica un CSV con
        el esquema esperado y se puede escribir en el padre de ``output_path``.
    Postcondiciones:
        Escribe en ``output_path`` un CSV no vacio, sin coordenadas faltantes,
        y retorna el mismo contenido como un nuevo ``DataFrame``; omite
        padrones invalidos y lanza ``ValueError`` cuando no logra convertirlos
        o completar todas las ubicaciones.
    """
    padrones = listar_padrones(padrones_dir)
    if not padrones:
        raise ValueError(f"No se encontraron archivos .xlsx en {padrones_dir}")

    primaria = _cargar_primaria(primaria_url)
    resultados = []

    for padron_path in padrones:
        try:
            escuelas = _combinar_padron_con_primaria(
                padron_path,
                primaria,
                conservar_sin_coordenadas=True,
            )
        except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
            LOGGER.warning("Se omite %s: %s", padron_path, exc)
            continue

        if escuelas.empty:
            LOGGER.warning(
                "Se omite %s: no tiene escuelas primarias estatales de Dolores",
                padron_path,
            )
            continue

        nombre_padron = _nombre_padron(padron_path)
        escuelas = escuelas.copy()
        escuelas.insert(0, "padron_archivo", padron_path.name)
        etiqueta_padron = _etiqueta_padron(f"Padrón {nombre_padron}")
        escuelas.insert(0, "padron_nombre", etiqueta_padron)
        escuelas.insert(0, "padron", _padron_id(nombre_padron))
        resultados.append(escuelas)

    if not resultados:
        raise ValueError("No se pudo convertir ningun padron valido")

    padrones_csv = pd.concat(resultados, ignore_index=True, sort=False)
    padrones_csv = _completar_coordenadas_mas_recientes(padrones_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    padrones_csv.to_csv(output_path, index=False, encoding="utf-8")
    return padrones_csv


def _completar_coordenadas_mas_recientes(
    padrones: pd.DataFrame,
) -> pd.DataFrame:
    """Completa coordenadas faltantes con el dato disponible mas reciente.

    Precondiciones:
        ``padrones`` contiene ``Cueanexo``, ``Departamento``, ``Localidad``,
        ``Domicilio``, ``latitud`` y ``longitud``; sus filas estan ordenadas
        cronologicamente, desde el padron mas antiguo al mas reciente.
    Postcondiciones:
        Retorna una copia sin coordenadas faltantes. Cada fila incompleta usa
        el ultimo par disponible para su ``Cueanexo`` o, como respaldo, para
        su mismo departamento, localidad y domicilio. Las coordenadas oficiales
        configuradas prevalecen sobre las demas fuentes; lanza ``ValueError`` si
        no puede completar alguna escuela.
    """
    resultado = padrones.copy()
    cueanexos_numericos = pd.to_numeric(resultado["Cueanexo"], errors="coerce")
    for cueanexo, (latitud, longitud) in COORDENADAS_OFICIALES.items():
        escuela = cueanexos_numericos.eq(cueanexo)
        resultado.loc[escuela, "latitud"] = latitud
        resultado.loc[escuela, "longitud"] = longitud

    coordenadas_completas = resultado.dropna(subset=["latitud", "longitud"])
    coordenadas_recientes = coordenadas_completas.drop_duplicates(
        subset=["Cueanexo"],
        keep="last",
    ).set_index("Cueanexo")[["latitud", "longitud"]]

    latitud_reciente = resultado["Cueanexo"].map(coordenadas_recientes["latitud"])
    longitud_reciente = resultado["Cueanexo"].map(coordenadas_recientes["longitud"])
    tiene_dato_reciente = latitud_reciente.notna() & longitud_reciente.notna()
    necesita_coordenadas = resultado[["latitud", "longitud"]].isna().any(axis=1)
    completar = necesita_coordenadas & tiene_dato_reciente

    resultado.loc[completar, "latitud"] = latitud_reciente[completar]
    resultado.loc[completar, "longitud"] = longitud_reciente[completar]

    columnas_ubicacion = ["Departamento", "Localidad", "Domicilio"]
    claves_normalizadas = []
    for columna in columnas_ubicacion:
        clave = f"_{columna.casefold()}_normalizado"
        resultado[clave] = (
            resultado[columna].fillna("").astype(str).str.strip().str.casefold()
        )
        claves_normalizadas.append(clave)

    coordenadas_por_ubicacion = (
        resultado.dropna(subset=["latitud", "longitud"])
        .loc[lambda filas: filas[claves_normalizadas].ne("").all(axis=1)]
        .drop_duplicates(subset=claves_normalizadas, keep="last")
        .set_index(claves_normalizadas)[["latitud", "longitud"]]
    )
    ubicaciones = pd.MultiIndex.from_frame(resultado[claves_normalizadas])
    latitud_ubicacion = pd.Series(
        coordenadas_por_ubicacion["latitud"].reindex(ubicaciones).to_numpy(),
        index=resultado.index,
    )
    longitud_ubicacion = pd.Series(
        coordenadas_por_ubicacion["longitud"].reindex(ubicaciones).to_numpy(),
        index=resultado.index,
    )
    necesita_coordenadas = resultado[["latitud", "longitud"]].isna().any(axis=1)
    tiene_dato_ubicacion = latitud_ubicacion.notna() & longitud_ubicacion.notna()
    completar = necesita_coordenadas & tiene_dato_ubicacion
    resultado.loc[completar, "latitud"] = latitud_ubicacion[completar]
    resultado.loc[completar, "longitud"] = longitud_ubicacion[completar]
    resultado = resultado.drop(columns=claves_normalizadas)

    faltantes = resultado[["latitud", "longitud"]].isna().any(axis=1)
    if faltantes.any():
        cueanexos = ", ".join(
            sorted(resultado.loc[faltantes, "Cueanexo"].astype(str).unique())
        )
        mensaje = f"No se encontraron coordenadas para los Cueanexo: {cueanexos}"
        raise ValueError(mensaje)

    return resultado


def _padron_id(nombre_padron: str) -> str:
    """Normaliza el nombre de un padron como identificador estable.

    Precondiciones:
        ``nombre_padron`` es una cadena.
    Postcondiciones:
        Retorna una cadena con prefijo ``padron_``, sin caracteres no
        alfanumericos internos salvo guiones bajos.
    """
    valor = re.sub(r"\W+", "_", nombre_padron, flags=re.ASCII).strip("_")
    return f"padron_{valor}"


def _parse_args() -> argparse.Namespace:
    """Interpreta los argumentos de linea de comandos del conversor.

    Precondiciones:
        Los argumentos del proceso respetan las opciones definidas por el
        parser o permiten que ``argparse`` informe el error.
    Postcondiciones:
        Retorna un ``Namespace`` con ``padrones_dir``, ``salida`` y
        ``primaria_url``; no modifica archivos.
    """
    parser = argparse.ArgumentParser(
        description="Genera padrones.csv desde todos los XLSX disponibles."
    )
    parser.add_argument(
        "--padrones-dir",
        type=Path,
        default=PADRONES_DIR,
        help="Directorio donde buscar archivos .xlsx.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=PADRONES_CSV_PATH,
        help="Archivo CSV de salida.",
    )
    parser.add_argument(
        "--primaria-url",
        default=PRIMARIA_URL,
        help="CSV remoto/local de escuelas primarias usado para coordenadas.",
    )
    return parser.parse_args()


def main() -> None:
    """Ejecuta la conversion de padrones desde la linea de comandos.

    Precondiciones:
        Los argumentos y las fuentes cumplen los contratos de
        :func:`_parse_args` y :func:`convertir_padrones`.
    Postcondiciones:
        Configura el logging, genera el CSV, informa su ruta y cantidad de
        filas por salida estandar, y retorna ``None``.
    """
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    args = _parse_args()
    padrones = convertir_padrones(
        padrones_dir=args.padrones_dir,
        output_path=args.salida,
        primaria_url=args.primaria_url,
    )
    print(f"CSV generado: {args.salida} ({len(padrones)} filas)")


if __name__ == "__main__":
    main()
