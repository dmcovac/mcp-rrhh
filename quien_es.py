"""Traduce un código de candidato (C-0042) a su nombre. Solo para la persona responsable.

Esta herramienta NO es del servidor MCP: la IA no puede usarla. Es la otra mitad
de la seudonimización: la IA solo ve códigos, y la persona autorizada puede
reidentificar cuando lo necesita, con la tabla que se guarda aparte (RGPD art. 4.5).

Uso:
    python quien_es.py C-0042
"""

import json
import sys
from pathlib import Path

CODIGOS = Path.home() / "developer" / "mcp-rrhh-datos" / "codigos_candidatos.json"

if len(sys.argv) != 2:
    sys.exit("Uso: python quien_es.py C-0042")

if not CODIGOS.exists():
    sys.exit(f"No encuentro la tabla de códigos en {CODIGOS}")

codigo = sys.argv[1].strip().upper()
tabla = json.loads(CODIGOS.read_text(encoding="utf-8"))
encontrado = next((d for d in tabla.values() if d["codigo"] == codigo), None)

if encontrado:
    print(f"{codigo} es {encontrado['nombre']}. Búscalo por ese nombre en Zoho Recruit.")
else:
    print(f"No hay ningún candidato con el código {codigo}.")
