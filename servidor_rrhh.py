import json
from pathlib import Path

from fastmcp import FastMCP

servidor = FastMCP("rrhh")

# Los candidatos viven en este archivo. Se crea con generar_candidatos.py.
ARCHIVO = Path(__file__).parent / "candidatos.json"


def leer_candidatos() -> list[dict]:
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def guardar_candidatos(candidatos: list[dict]) -> None:
    ARCHIVO.write_text(json.dumps(candidatos, ensure_ascii=False, indent=2), encoding="utf-8")


CANDIDATOS = leer_candidatos()


@servidor.tool
def listar_candidatos() -> list[dict]:
    """Devuelve la lista completa de candidatos del proceso de selección,
    con su nombre, el puesto al que optan y la fase en la que están."""
    return CANDIDATOS

@servidor.tool
def buscar_candidatos(puesto: str = "", fase: str = "") -> list[dict]:
    """Busca candidatos filtrando por puesto y/o fase del proceso.
    Si no se indica ningún filtro, devuelve todos los candidatos.
    Ejemplos de puesto: 'Data Engineer', 'Consultor MDM'.
    Ejemplos de fase: 'Criba curricular', 'Entrevista técnica', 'Oferta enviada'."""
    resultado = []
    for candidato in CANDIDATOS:
        if puesto and puesto.lower() not in candidato["puesto"].lower():
            continue
        if fase and fase.lower() not in candidato["fase"].lower():
            continue
        resultado.append(candidato)
    return resultado

@servidor.tool
def cambiar_fase(nombre: str, nueva_fase: str, confirmar: bool = False) -> dict:
    """Cambia la fase del proceso de selección de un candidato.
    IMPORTANTE: esta operación modifica datos. Llama primero sin confirmar
    para ver qué cambiaría, muestra el resultado al usuario, y solo vuelve
    a llamar con confirmar=True si el usuario lo aprueba explícitamente."""
    encontrados = [c for c in CANDIDATOS if nombre.lower() in c["nombre"].lower()]

    if len(encontrados) == 0:
        return {"estado": "error", "mensaje": f"No encuentro a nadie llamado '{nombre}'."}
    if len(encontrados) > 1:
        nombres = [c["nombre"] for c in encontrados]
        return {"estado": "error", "mensaje": f"'{nombre}' coincide con varias personas: {nombres}. Concreta más."}

    candidato = encontrados[0]

    if not confirmar:
        return {
            "estado": "pendiente_de_confirmacion",
            "mensaje": f"Esto cambiaría a {candidato['nombre']} de '{candidato['fase']}' a '{nueva_fase}'. No se ha modificado nada todavía. Pide aprobación al usuario y vuelve a llamar con confirmar=True.",
        }

    fase_anterior = candidato["fase"]
    candidato["fase"] = nueva_fase
    guardar_candidatos(CANDIDATOS)
    return {
        "estado": "hecho",
        "mensaje": f"{candidato['nombre']}: '{fase_anterior}' → '{nueva_fase}'.",
    }

if __name__ == "__main__":
    servidor.run()