"""Crea el archivo candidatos.json con candidatos falsos en español.

Se ejecuta una sola vez:  python generar_candidatos.py
Si candidatos.json ya existe no lo toca, para no perder los cambios
de fase guardados. Para empezar de cero:  python generar_candidatos.py --sobrescribir
"""
import json
import sys
from pathlib import Path

from faker import Faker

ARCHIVO = Path.home() / "developer" / "mcp-rrhh-datos" / "candidatos.json"

PUESTOS = ["Data Engineer", "Consultor MDM", "Project Manager", "Analista de datos", "Arquitecto cloud"]
FASES = ["Criba curricular", "Entrevista RRHH", "Entrevista técnica", "Oferta enviada", "Contratado", "Descartado"]


def generar_candidatos(cantidad: int = 50, semilla: int = 42) -> list[dict]:
    """Crea candidatos falsos en español. Con la misma semilla salen
    siempre los mismos."""
    fake = Faker("es_ES")
    fake.seed_instance(semilla)
    candidatos = []
    nombres_usados = set()
    while len(candidatos) < cantidad:
        nombre = f"{fake.first_name()} {fake.last_name()}"
        if nombre in nombres_usados:
            continue
        nombres_usados.add(nombre)
        candidatos.append({
            "nombre": nombre,
            "puesto": fake.random_element(PUESTOS),
            "fase": fake.random_element(FASES),
        })
    return candidatos


if __name__ == "__main__":
    if ARCHIVO.exists() and "--sobrescribir" not in sys.argv:
        print(f"{ARCHIVO.name} ya existe, no lo toco. Usa --sobrescribir para empezar de cero.")
        sys.exit(1)
    candidatos = generar_candidatos()
    ARCHIVO.write_text(json.dumps(candidatos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Creado {ARCHIVO.name} con {len(candidatos)} candidatos.")
