import csv
import functools
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values
from fastmcp import FastMCP

servidor = FastMCP("rrhh")

# Los candidatos viven en Zoho Recruit. El servidor usa sus propias llaves,
# que solo pueden leer candidaturas y cambiar el estado de un candidato.
LLAVES = dotenv_values(Path(__file__).parent / ".env")
URL_TOKEN = "https://accounts.zoho.eu/oauth/v2/token"
URL_API = "https://recruit.zoho.eu/recruit/v2"

# Fases que se pueden poner: nombre en pantalla -> valor interno de Zoho.
FASES = {
    "En revisión": "In Review",
    "Entrevista programada": "Interview-Scheduled",
    "Oferta realizada": "Offer-Made",
    "Contratado": "Hired",
    "Rechazado": "Rejected",
}

# Registro de cada llamada: qué se pidió, cuándo y qué se devolvió.
# Contiene nombres de candidatos, así que vive fuera de la carpeta del proyecto
# (y por tanto fuera de git), junto a los demás datos.
REGISTRO = Path.home() / "developer" / "mcp-rrhh-datos" / "registro_mcp.csv"

_token = {"valor": None, "caduca": 0.0}


def zoho() -> httpx.Client:
    # El token de acceso dura una hora: se pide uno nuevo solo cuando caduca.
    if time.time() > _token["caduca"]:
        respuesta = httpx.post(URL_TOKEN, data={
            "grant_type": "refresh_token",
            "client_id": LLAVES["ZOHO_CLIENT_ID"],
            "client_secret": LLAVES["ZOHO_CLIENT_SECRET"],
            "refresh_token": LLAVES["ZOHO_REFRESH_TOKEN_SERVIDOR"],
        }).json()
        _token["valor"] = respuesta["access_token"]
        _token["caduca"] = time.time() + respuesta.get("expires_in", 3600) - 60
    return httpx.Client(base_url=URL_API, headers={"Authorization": f"Zoho-oauthtoken {_token['valor']}"}, timeout=30)


def leer_candidaturas() -> list[dict]:
    with zoho() as cliente:
        return cliente.get("/Applications", params={"per_page": 200}).json().get("data", [])


def minimizar(candidatura: dict) -> dict:
    # Zoho devuelve email, reclutador, cliente, fechas... La IA solo necesita esto.
    return {
        "nombre": candidatura["Full_Name"],
        "puesto": candidatura["Posting_Title"],
        "fase": candidatura["Application_Status"],
    }


def registrar(herramienta):
    @functools.wraps(herramienta)
    def con_registro(*args, **kwargs):
        try:
            resultado = herramienta(*args, **kwargs)
        except Exception as error:
            resultado = {"estado": "error", "mensaje": f"Fallo interno: {error}"}
            raise
        finally:
            nuevo = not REGISTRO.exists()
            REGISTRO.parent.mkdir(parents=True, exist_ok=True)
            with open(REGISTRO, "a", newline="", encoding="utf-8-sig" if nuevo else "utf-8") as f:
                escritor = csv.writer(f)
                if nuevo:
                    escritor.writerow(["fecha", "herramienta", "se_pidio", "se_devolvio"])
                escritor.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    herramienta.__name__,
                    json.dumps(kwargs, ensure_ascii=False),
                    json.dumps(resultado, ensure_ascii=False),
                ])
        return resultado
    return con_registro


@servidor.tool
@registrar
def listar_candidatos() -> list[dict]:
    """Devuelve la lista completa de candidatos del proceso de selección,
    con su nombre, el puesto al que optan y la fase en la que están."""
    return [minimizar(c) for c in leer_candidaturas()]

@servidor.tool
@registrar
def buscar_candidatos(puesto: str = "", fase: str = "") -> list[dict]:
    """Busca candidatos filtrando por puesto y/o fase del proceso.
    Si no se indica ningún filtro, devuelve todos los candidatos.
    Ejemplos de puesto: 'Data Engineer', 'Consultor MDM'.
    Fases posibles: 'En revisión', 'Entrevista programada', 'Oferta realizada',
    'Contratado', 'Rechazado'."""
    resultado = []
    for candidato in [minimizar(c) for c in leer_candidaturas()]:
        if puesto and puesto.lower() not in candidato["puesto"].lower():
            continue
        if fase and fase.lower() not in candidato["fase"].lower():
            continue
        resultado.append(candidato)
    return resultado

@servidor.tool
@registrar
def cambiar_fase(nombre: str, nueva_fase: str, confirmar: bool = False) -> dict:
    """Cambia la fase del proceso de selección de un candidato en Zoho Recruit.
    Fases posibles: 'En revisión', 'Entrevista programada', 'Oferta realizada',
    'Contratado', 'Rechazado'.
    IMPORTANTE: esta operación modifica datos. Llama primero sin confirmar
    para ver qué cambiaría, muestra el resultado al usuario, y solo vuelve
    a llamar con confirmar=True si el usuario lo aprueba explícitamente."""
    fase_zoho = next((v for k, v in FASES.items() if k.lower() == nueva_fase.lower()), None)
    if not fase_zoho:
        return {"estado": "error", "mensaje": f"'{nueva_fase}' no es una fase válida. Usa una de: {list(FASES)}."}

    candidaturas = leer_candidaturas()
    encontrados = [c for c in candidaturas if nombre.lower() in c["Full_Name"].lower()]

    if len(encontrados) == 0:
        return {"estado": "error", "mensaje": f"No encuentro a nadie llamado '{nombre}'."}
    if len(encontrados) > 1:
        nombres = [f"{c['Full_Name']} ({c['Posting_Title']})" for c in encontrados]
        return {"estado": "error", "mensaje": f"'{nombre}' coincide con varias candidaturas: {nombres}. Concreta más."}

    candidatura = encontrados[0]
    actual = minimizar(candidatura)

    if not confirmar:
        aviso = ""
        if fase_zoho == "Hired":
            contratados = sum(1 for c in candidaturas
                              if c["$Job_Opening_Id"] == candidatura["$Job_Opening_Id"] and c["Application_Status"] == "Contratado")
            aviso = (f" OJO: ya hay {contratados} contratado(s) en {actual['puesto']}. Si con este se llega al "
                     "número de puestos de la vacante, Zoho la cerrará y archivará a los demás candidatos en proceso.")
        return {
            "estado": "pendiente_de_confirmacion",
            "mensaje": f"Esto cambiaría a {actual['nombre']} ({actual['puesto']}) de '{actual['fase']}' a '{nueva_fase}'. "
                       f"No se ha modificado nada todavía.{aviso} Pide aprobación al usuario y vuelve a llamar con confirmar=True.",
        }

    with zoho() as cliente:
        respuesta = cliente.put("/Candidates/status", json={"data": [{
            "ids": [candidatura["$Candidate_Id"]],
            "jobids": [candidatura["$Job_Opening_Id"]],
            "Candidate_Status": fase_zoho,
            "comments": "Cambiado desde el servidor MCP",
        }]}).json()
    codigo = (respuesta.get("data") or [{}])[0].get("code")
    if codigo != "SUCCESS":
        return {"estado": "error", "mensaje": f"Zoho no ha hecho el cambio: {codigo or respuesta}."}
    return {
        "estado": "hecho",
        "mensaje": f"{actual['nombre']} ({actual['puesto']}): '{actual['fase']}' → '{nueva_fase}'.",
    }

if __name__ == "__main__":
    servidor.run()
