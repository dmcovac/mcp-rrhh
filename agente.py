"""Agente de selección con capa de privacidad.

El agente habla con Claude por la API y solo puede llegar a los datos a
través del servidor MCP (servidor_rrhh.py). Por eso nunca ve nombres,
emails ni móviles: solo códigos, puestos y fases.

Uso:
    python agente.py

Necesita ANTHROPIC_API_KEY en el archivo .env (que no se sube a git).
"""

import asyncio
import csv
import json
import os
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastmcp import Client

CARPETA = Path(__file__).parent
load_dotenv(CARPETA / ".env")

# Modelo: Haiku 5.5 por coste (ver memoria, módulo 1). Se puede cambiar con
# la variable MODELO, por ejemplo MODELO=claude-sonnet-5-5.
MODELO = os.getenv("MODELO", "claude-haiku-5-5")

# Precio en dólares por millón de tokens (entrada, salida). Octubre de 2026.
PRECIOS = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

# Herramientas que cambian datos. El hook para el agente antes de usarlas.
ESCRITURAS = {"cambiar_fase"}

# Gasto del agente: fuera del proyecto y de git, junto al registro del servidor.
REGISTRO_AGENTE = Path.home() / "developer" / "mcp-rrhh-datos" / "registro_agente.csv"

# Cada decisión de la persona en el hook (sí o no). La AEPD pide que la
# supervisión humana sea real y que quede constancia de los desacuerdos.
REGISTRO_DECISIONES = REGISTRO_AGENTE.parent / "registro_decisiones.csv"

MAX_VUELTAS = 10

INSTRUCCIONES = """Eres un asistente de RRHH que ayuda a gestionar un proceso de selección.
Solo puedes conocer a los candidatos a través de tus herramientas.
Los candidatos se identifican por un código (C-0001, C-0002...). No conoces sus nombres
ni otros datos personales, y no debes intentar adivinarlos ni pedirlos.
Para cambiar la fase de un candidato: primero llama a cambiar_fase sin confirmar para ver
qué cambiaría y explícaselo a la persona. Después llama con confirmar=True: el sistema le
pedirá a la persona que lo apruebe antes de hacer nada.
Responde en español, de forma breve y clara."""


def hook_antes_de_herramienta(nombre: str, argumentos: dict) -> str | None:
    """Se ejecuta antes de cada herramienta, fuera del alcance del modelo.

    Devuelve None si la herramienta puede ejecutarse, o un mensaje si se bloquea.
    Una escritura con confirmar=True solo pasa si una persona responde s, si o sí.
    """
    if nombre not in ESCRITURAS or not argumentos.get("confirmar"):
        return None
    print(f"\n⚠️  El agente quiere CAMBIAR datos: {nombre} {json.dumps(argumentos, ensure_ascii=False)}")
    respuesta = input("¿Confirmas el cambio? (s/n): ").strip().lower()
    # Solo un sí claro deja pasar el cambio. Cualquier otra cosa cuenta como no:
    # ante la duda, no se toca nada.
    aprobado = respuesta in {"s", "si", "sí"}
    apuntar_decision(nombre, argumentos, respuesta, aprobado)
    if aprobado:
        return None
    print("   Cambio cancelado: no se ha modificado nada.")
    return ("La persona responsable ha respondido que NO al cambio. No se ha modificado nada. "
            "No lo intentes de nuevo salvo que ella lo pida.")


def apuntar_decision(nombre: str, argumentos: dict, respuesta: str, aprobado: bool) -> None:
    nuevo = not REGISTRO_DECISIONES.exists()
    REGISTRO_DECISIONES.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRO_DECISIONES, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:
            escritor.writerow(["fecha", "herramienta", "argumentos", "respuesta", "decision"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), nombre,
                           json.dumps(argumentos, ensure_ascii=False), respuesta,
                           "aprobado" if aprobado else "rechazado"])


def apuntar_gasto(entrada: int, salida: int, herramientas: int) -> float:
    precio_entrada, precio_salida = PRECIOS.get(MODELO, (0, 0))
    coste = (entrada * precio_entrada + salida * precio_salida) / 1_000_000
    nuevo = not REGISTRO_AGENTE.exists()
    REGISTRO_AGENTE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRO_AGENTE, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:
            escritor.writerow(["fecha", "modelo", "tokens_entrada", "tokens_salida", "herramientas_usadas", "coste_usd"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), MODELO, entrada, salida, herramientas, f"{coste:.6f}"])
    return coste


async def responder(claude: AsyncAnthropic, servidor: Client, herramientas: list, historial: list) -> None:
    entrada = salida = usadas = 0
    for _ in range(MAX_VUELTAS):
        respuesta = await claude.messages.create(
            model=MODELO, max_tokens=1024, system=INSTRUCCIONES,
            tools=herramientas, messages=historial,
        )
        entrada += respuesta.usage.input_tokens
        salida += respuesta.usage.output_tokens
        historial.append({"role": "assistant", "content": respuesta.content})

        if respuesta.stop_reason != "tool_use":
            texto = "".join(b.text for b in respuesta.content if b.type == "text")
            print(f"\nAgente: {texto}")
            break

        resultados = []
        for bloque in respuesta.content:
            if bloque.type != "tool_use":
                continue
            usadas += 1
            print(f"   · usa {bloque.name} {json.dumps(bloque.input, ensure_ascii=False)}")
            bloqueo = hook_antes_de_herramienta(bloque.name, bloque.input)
            if bloqueo:
                contenido = bloqueo
            else:
                try:
                    resultado = await servidor.call_tool(bloque.name, bloque.input)
                    contenido = "\n".join(c.text for c in resultado.content if hasattr(c, "text"))
                except Exception as error:
                    contenido = f"Error al usar la herramienta: {error}"
            resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": contenido})
        historial.append({"role": "user", "content": resultados})
    else:
        print("\nAgente: he llegado al límite de pasos sin terminar. Prueba a concretar la pregunta.")

    coste = apuntar_gasto(entrada, salida, usadas)
    print(f"   [{entrada} tokens de entrada, {salida} de salida, {coste:.4f} $]")


async def main() -> None:
    claude = AsyncAnthropic()
    async with Client(str(CARPETA / "servidor_rrhh.py")) as servidor:
        herramientas = [
            {"name": h.name, "description": h.description or "", "input_schema": h.inputSchema}
            for h in await servidor.list_tools()
        ]
        print(f"Agente de selección ({MODELO}). Herramientas: {', '.join(h['name'] for h in herramientas)}")
        print("Escribe tu pregunta, o 'salir' para terminar.")
        historial: list = []
        while True:
            pregunta = input("\nTú: ").strip()
            if pregunta.lower() in {"salir", "exit", "quit"}:
                break
            if pregunta:
                historial.append({"role": "user", "content": pregunta})
                await responder(claude, servidor, herramientas, historial)


if __name__ == "__main__":
    asyncio.run(main())
