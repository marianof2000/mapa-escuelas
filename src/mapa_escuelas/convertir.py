# -*- coding: utf-8 -*-
"""Convierte los padrones XLSX en un CSV unico listo para el mapa."""

import argparse
import logging
from pathlib import Path
import re

import pandas as pd

from .config import PADRONES_CSV_PATH, PADRONES_DIR, PRIMARIA_URL
from .funciones import (
    _cargar_primaria,
    _combinar_padron_con_primaria,
    _nombre_padron,
    listar_padrones,
)


LOGGER = logging.getLogger(__name__)


def convertir_padrones(
    padrones_dir: Path = PADRONES_DIR,
    output_path: Path = PADRONES_CSV_PATH,
    primaria_url: str = PRIMARIA_URL,
) -> pd.DataFrame:
    padrones = listar_padrones(padrones_dir)
    if not padrones:
        raise ValueError(f"No se encontraron archivos .xlsx en {padrones_dir}")

    primaria_dolores = _cargar_primaria(primaria_url)
    resultados = []

    for padron_path in padrones:
        try:
            escuelas = _combinar_padron_con_primaria(padron_path, primaria_dolores)
        except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
            LOGGER.warning("Se omite %s: %s", padron_path, exc)
            continue

        if escuelas.empty:
            LOGGER.warning("Se omite %s: no tiene escuelas con coordenadas", padron_path)
            continue

        nombre_padron = _nombre_padron(padron_path)
        escuelas = escuelas.copy()
        escuelas.insert(0, "padron_archivo", padron_path.name)
        escuelas.insert(0, "padron_nombre", f"Padrón {nombre_padron}")
        escuelas.insert(0, "padron", _padron_id(nombre_padron))
        resultados.append(escuelas)

    if not resultados:
        raise ValueError("No se pudo convertir ningun padron valido")

    padrones_csv = pd.concat(resultados, ignore_index=True, sort=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    padrones_csv.to_csv(output_path, index=False, encoding="utf-8")
    return padrones_csv


def _padron_id(nombre_padron: str) -> str:
    valor = re.sub(r"\W+", "_", nombre_padron, flags=re.ASCII).strip("_")
    return f"padron_{valor}"


def _parse_args() -> argparse.Namespace:
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
