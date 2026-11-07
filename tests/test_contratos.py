# -*- coding: utf-8 -*-
"""Validaciones de type hints y contratos para todo el codigo Python."""

import ast
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIRS = (PROJECT_ROOT / "src", PROJECT_ROOT / "tests")


class ContratosPythonTest(unittest.TestCase):
    """Comprueba las convenciones obligatorias de las funciones Python."""

    def test_funciones_tienen_type_hints_y_contratos(self) -> None:
        """Verifica firmas tipadas y contratos completos en cada función.

        Precondiciones:
            Los directorios configurados contienen archivos Python analizables
            mediante ``ast``.
        Postcondiciones:
            La prueba finaliza correctamente solo si cada función declara los
            tipos de sus parámetros y retorno, además de las secciones
            ``Precondiciones:`` y ``Postcondiciones:`` en su docstring.
        """
        errores: list[str] = []
        for directorio in PYTHON_DIRS:
            for path in sorted(directorio.rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                modulo = ast.parse(path.read_text(encoding="utf-8"))
                for funcion in ast.walk(modulo):
                    if not isinstance(
                        funcion,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    ):
                        continue

                    argumentos = [
                        *funcion.args.posonlyargs,
                        *funcion.args.args,
                        *funcion.args.kwonlyargs,
                    ]
                    sin_tipo = [
                        argumento.arg
                        for argumento in argumentos
                        if argumento.arg not in {"self", "cls"}
                        and argumento.annotation is None
                    ]
                    if funcion.args.vararg and funcion.args.vararg.annotation is None:
                        sin_tipo.append(f"*{funcion.args.vararg.arg}")
                    if funcion.args.kwarg and funcion.args.kwarg.annotation is None:
                        sin_tipo.append(f"**{funcion.args.kwarg.arg}")
                    if sin_tipo:
                        errores.append(
                            f"{path}:{funcion.lineno} {funcion.name}: "
                            f"faltan tipos en {', '.join(sin_tipo)}"
                        )
                    if funcion.returns is None:
                        errores.append(
                            f"{path}:{funcion.lineno} {funcion.name}: "
                            "falta el tipo de retorno"
                        )

                    contrato = ast.get_docstring(funcion) or ""
                    if "Precondiciones:" not in contrato:
                        errores.append(
                            f"{path}:{funcion.lineno} {funcion.name}: "
                            "faltan precondiciones"
                        )
                    if "Postcondiciones:" not in contrato:
                        errores.append(
                            f"{path}:{funcion.lineno} {funcion.name}: "
                            "faltan postcondiciones"
                        )

        self.assertEqual([], errores, "\n" + "\n".join(errores))
