# AGENTS.md

## 1. Objetivo

Este proyecto está desarrollado en Python.

El agente debe ayudar a desarrollar, corregir y mantener el código, priorizando la claridad, simplicidad y buenas prácticas.

## 2. Reglas generales

- Utilizar Python 3 y respetar la versión definida en `pyproject.toml` o `.python-version`.
- Escribir código claro, legible y fácil de mantener.
- Seguir las convenciones de estilo PEP 8.
- Utilizar nombres descriptivos para variables, funciones y clases.
- Evitar código duplicado y complejidad innecesaria.
- Incorporar anotaciones de tipos (*type hints*) en las funciones.
- Utilizar `pathlib` para trabajar con rutas de archivos cuando corresponda.

## 3. Organización del código

- Respetar la estructura de directorios existente.
- Dividir el código en funciones y módulos con responsabilidades claras.
- Evitar modificar archivos que no estén relacionados con la tarea solicitada.
- No incorporar dependencias sin justificar su necesidad.

## 4. Gestión de dependencias

El proyecto utiliza `uv` para administrar Python y sus dependencias.

Comandos habituales:

```bash
uv sync
uv run python main.py
uv run pytest
```

No instalar dependencias globalmente.

## 5. Pruebas y validación

- Utilizar `pytest` para las pruebas automatizadas.
- Agregar o actualizar pruebas cuando se modifique una funcionalidad.
- Verificar que los cambios no afecten funcionalidades existentes.
- No eliminar pruebas para evitar errores.

## 6. Documentación

- Escribir en contrato con pre y post condiciones en cada función.
- Mantener actualizado el archivo `README.md` cuando corresponda.
- Utilizar comentarios solamente cuando aporten información relevante.
- Redactar documentación y explicaciones en español.

## 7. Seguridad

- No incorporar contraseñas, tokens ni claves privadas en el código.
- Utilizar variables de entorno para información sensible.
- No modificar ni eliminar datos reales sin autorización.

## 8. Forma de trabajo del agente

Antes de modificar el proyecto:

1. Revisar los archivos involucrados.
2. Explicar brevemente qué se necesita cambiar.
3. Implementar la solución más simple y adecuada.
4. Ejecutar las pruebas disponibles.
5. Informar los archivos modificados y los resultados de las pruebas.

No realizar refactorizaciones extensas que no hayan sido solicitadas.

## 9. Prioridades

Ante varias alternativas, priorizar:

1. Correctitud.
2. Legibilidad.
3. Simplicidad.
4. Mantenibilidad.
5. Rendimiento, cuando sea necesario.