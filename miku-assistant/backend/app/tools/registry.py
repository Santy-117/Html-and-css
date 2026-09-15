"""Declaración de tools expuestas al modelo (formato google-genai).

Solo se expone una función: `abrir_app_o_archivo`, y su único parámetro es un
enum generado dinámicamente a partir de las keys de allowlist.yaml. Esto hace
imposible, a nivel de esquema, que el modelo pida abrir algo que no esté en
la lista blanca — no es una validación "de buena fe" en el prompt, es una
restricción estructural de la función que Gemini puede llamar.
"""

from __future__ import annotations

from google.genai import types

from app.tools.actions import ToolActionError, list_allowlist, run_allowlisted_action


def build_tools() -> list[types.Tool] | None:
    entries = list_allowlist()
    if not entries:
        return None

    keys = sorted(entries)
    descriptions = "; ".join(f"{k}={v.description}" for k, v in entries.items())

    function = types.FunctionDeclaration(
        name="abrir_app_o_archivo",
        description=(
            "Abre una aplicación o archivo previamente autorizado por el usuario. "
            f"Opciones disponibles -> {descriptions}"
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "key": types.Schema(
                    type=types.Type.STRING,
                    enum=keys,
                    description="Identificador exacto de la app/archivo a abrir.",
                )
            },
            required=["key"],
        ),
    )
    return [types.Tool(function_declarations=[function])]


def dispatch_tool_call(name: str, args: dict) -> str:
    if name != "abrir_app_o_archivo":
        return f'Tool desconocida: "{name}".'

    key = args.get("key", "")
    try:
        return run_allowlisted_action(key)
    except ToolActionError as exc:
        return f"Error: {exc}"
