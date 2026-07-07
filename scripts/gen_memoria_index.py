#!/usr/bin/env python3
"""Genera el índice de `memoria/` y lo inyecta en AGENTS.md entre marcadores.

Convención: cada `memoria/*.md` empieza con un `# Título` (H1) y una primera
línea de cita `> descripción`. El generador toma ambos para construir la tabla.

Uso:
    python scripts/gen_memoria_index.py           # reescribe AGENTS.md
    python scripts/gen_memoria_index.py --check    # solo verifica (exit 1 si difiere)

Idempotente: si el índice ya está al día no cambia nada.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORIA_DIR = ROOT / "memoria"
AGENTS_FILE = ROOT / "AGENTS.md"

START_MARKER = "<!-- MEMORIA-INDEX:START -->"
END_MARKER = "<!-- MEMORIA-INDEX:END -->"

# Orden preferido; los no listados van al final por orden alfabético.
ORDER = [
    "handoff.md",
    "contexto.md",
    "arquitectura.md",
    "decisiones.md",
    "fuentes-datos.md",
    "fases.md",
    "convenciones.md",
    "bitacora.md",
]


def _read_meta(md_path: Path) -> tuple[str, str]:
    """Devuelve (título, descripción) de un fichero markdown."""
    title = md_path.stem
    description = ""
    for line in md_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and title == md_path.stem:
            title = stripped[2:].strip()
        elif stripped.startswith("> ") and not description:
            description = stripped[2:].strip()
            break
    return title, description


def _sort_key(name: str) -> tuple[int, str]:
    return (ORDER.index(name), "") if name in ORDER else (len(ORDER), name)


def build_index() -> str:
    files = sorted(
        (p for p in MEMORIA_DIR.glob("*.md")),
        key=lambda p: _sort_key(p.name),
    )
    lines = ["| Documento | Descripción |", "|-----------|-------------|"]
    for md in files:
        title, description = _read_meta(md)
        rel = md.relative_to(ROOT).as_posix()
        lines.append(f"| [{title}]({rel}) | {description} |")
    return "\n".join(lines)


def render(agents_text: str, index_table: str) -> str:
    if START_MARKER not in agents_text or END_MARKER not in agents_text:
        raise SystemExit(
            f"No se encontraron los marcadores en {AGENTS_FILE.name}. "
            f"Añade:\n{START_MARKER}\n{END_MARKER}"
        )
    pre = agents_text.split(START_MARKER)[0]
    post = agents_text.split(END_MARKER)[1]
    return f"{pre}{START_MARKER}\n{index_table}\n{END_MARKER}{post}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="solo verifica")
    args = parser.parse_args()

    agents_text = AGENTS_FILE.read_text(encoding="utf-8")
    new_text = render(agents_text, build_index())

    if new_text == agents_text:
        print("Índice de memoria/ ya está al día.")
        return 0

    if args.check:
        print("El índice de memoria/ está desactualizado. Ejecuta "
              "`python scripts/gen_memoria_index.py`.", file=sys.stderr)
        return 1

    AGENTS_FILE.write_text(new_text, encoding="utf-8", newline="\n")
    print("Índice de memoria/ regenerado en AGENTS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
