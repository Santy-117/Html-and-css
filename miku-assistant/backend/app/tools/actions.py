"""Ejecución segura de acciones sobre el sistema.

Principio de seguridad: esta capa nunca recibe una ruta ni un comando
proveniente del modelo. Solo recibe una "key" (string corta, validada contra
la allowlist) y resuelve internamente a la ruta real configurada por el
usuario en allowlist.yaml. No se usa shell=True en ningún punto, así que no
hay forma de inyectar `&&`, `;`, `|`, etc. incluso si alguien lograra hacer
que el modelo "alucine" una key rara: si no está en el YAML, se rechaza.
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from app.config import ALLOWLIST_PATH


class ToolActionError(Exception):
    pass


@dataclass(frozen=True)
class AllowlistEntry:
    key: str
    kind: Literal["apps", "files"]
    description: str
    path: str
    args: tuple[str, ...] = ()


def _load_allowlist() -> dict[str, AllowlistEntry]:
    if not ALLOWLIST_PATH.exists():
        return {}

    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8")) or {}
    entries: dict[str, AllowlistEntry] = {}

    for kind in ("apps", "files"):
        for key, cfg in (raw.get(kind) or {}).items():
            entries[key] = AllowlistEntry(
                key=key,
                kind=kind,
                description=cfg.get("description", key),
                path=cfg["path"],
                args=tuple(cfg.get("args", [])),
            )
    return entries


def list_allowlist() -> dict[str, AllowlistEntry]:
    """Recarga el YAML en cada llamada para permitir editarlo sin reiniciar."""
    return _load_allowlist()


def describe_allowlist_for_prompt() -> str:
    entries = list_allowlist()
    if not entries:
        return "(no hay apps ni archivos configurados todavía)"
    lines = []
    for entry in entries.values():
        lines.append(f'- "{entry.key}" ({entry.kind[:-1]}): {entry.description}')
    return "\n".join(lines)


def run_allowlisted_action(key: str) -> str:
    """Abre la app/archivo identificado por `key`. Lanza ToolActionError si
    la key no existe en la allowlist o si la ruta configurada no existe en
    disco."""
    entries = list_allowlist()
    entry = entries.get(key)

    if entry is None:
        valid_keys = ", ".join(sorted(entries)) or "(ninguna configurada)"
        raise ToolActionError(
            f'La acción "{key}" no está permitida. Claves válidas: {valid_keys}'
        )

    target = Path(entry.path)
    if not target.exists():
        raise ToolActionError(
            f'La ruta configurada para "{key}" no existe en disco: {entry.path}. '
            "Revisa app/tools/allowlist.yaml."
        )

    system = platform.system()
    try:
        if entry.kind == "apps":
            subprocess.Popen([str(target), *entry.args], shell=False)
        else:  # files: abrir con la app predeterminada del sistema
            if system == "Windows":
                import os

                os.startfile(str(target))  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.Popen(["open", str(target)], shell=False)
            else:
                subprocess.Popen(["xdg-open", str(target)], shell=False)
    except OSError as exc:
        raise ToolActionError(f'No se pudo abrir "{key}": {exc}') from exc

    return f'Listo, abrí "{entry.description}".'
