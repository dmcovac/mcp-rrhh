"""Asocia cada candidato de candidatos_zoho.csv a su vacante en Zoho Recruit
y le pone el estado que le corresponde en el Hiring Pipeline.

Igual que cambiar_fase, primero enseña y después actúa:
  python cargar_en_zoho.py          solo muestra lo que haría, no cambia nada
  python cargar_en_zoho.py --uno    lo hace con el primer candidato, para revisarlo en Zoho
  python cargar_en_zoho.py --todos  lo hace con todos
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import dotenv_values

CARPETA = Path(__file__).parent
URL_TOKEN = "https://accounts.zoho.eu/oauth/v2/token"
URL_API = "https://recruit.zoho.eu/recruit/v2"
# Los datos de candidatos viven fuera de la carpeta del servidor, para que la IA no los lea.
ARCHIVO_CSV = Path.home() / "developer" / "mcp-rrhh-datos" / "candidatos_zoho.csv"

# Nuestra fase -> valor interno de Zoho (en pantalla sale traducido).
FASE_A_ZOHO = {
    "Criba curricular": "In Review",                # En revisión
    "Entrevista RRHH": "Interview-Scheduled",       # Entrevista programada
    "Entrevista técnica": "Interview-Scheduled",    # Entrevista programada
    "Oferta enviada": "Offer-Made",                # Oferta realizada
    "Contratado": "Hired",                         # Contratado
    "Descartado": "Rejected",                      # Rechazado
}


def conectar() -> httpx.Client:
    llaves = dotenv_values(CARPETA / ".env")
    token = httpx.post(URL_TOKEN, data={
        "grant_type": "refresh_token",
        "client_id": llaves["ZOHO_CLIENT_ID"],
        "client_secret": llaves["ZOHO_CLIENT_SECRET"],
        "refresh_token": llaves["ZOHO_REFRESH_TOKEN"],
    }).json()["access_token"]
    return httpx.Client(base_url=URL_API, headers={"Authorization": f"Zoho-oauthtoken {token}"}, timeout=30)


def preparar_plan(zoho: httpx.Client) -> list[dict]:
    candidatos_zoho = zoho.get("/Candidates", params={"per_page": 200}).json().get("data", [])
    id_por_email = {c["Email"].lower(): c["id"] for c in candidatos_zoho if c.get("Email")}
    vacantes = zoho.get("/JobOpenings").json().get("data", [])
    id_por_vacante = {v["Posting_Title"].lower(): v["id"] for v in vacantes}
    puestos_por_vacante = {v["Posting_Title"].lower(): int(v.get("Number_of_Positions") or 1) for v in vacantes}

    with open(ARCHIVO_CSV, encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))

    plan = []
    for fila in filas:
        plan.append({
            "nombre": f"{fila['First Name']} {fila['Last Name']}",
            "puesto": fila["Puesto"],
            "estado": FASE_A_ZOHO[fila["Fase"]],
            "candidato_id": id_por_email.get(fila["Email"].lower()),
            "vacante_id": id_por_vacante.get(fila["Puesto"].lower()),
        })

    # Si una vacante se llena, Zoho la cierra y archiva a los que siguen en proceso.
    # Por eso se para si hay tantos contratados como puestos, y los contratados van al final.
    contratados = Counter(p["puesto"].lower() for p in plan if p["estado"] == "Hired")
    for puesto, cantidad in contratados.items():
        if puesto in puestos_por_vacante and cantidad >= puestos_por_vacante[puesto]:
            sys.exit(f"PARO: '{puesto}' tendría {cantidad} contratados y solo tiene "
                     f"{puestos_por_vacante[puesto]} puestos en Zoho. Zoho la cerraría. "
                     "Sube el número de puestos de esa vacante y vuelve a ejecutar.")
    plan.sort(key=lambda p: p["estado"] == "Hired")
    return plan


def aplicar(zoho: httpx.Client, paso: dict) -> str:
    asociar = zoho.put("/Candidates/actions/associate", json={"data": [{
        "ids": [paso["candidato_id"]], "jobids": [paso["vacante_id"]], "comments": "Carga inicial",
    }]}).json()
    estado = zoho.put("/Candidates/status", json={"data": [{
        "ids": [paso["candidato_id"]], "jobids": [paso["vacante_id"]],
        "Candidate_Status": paso["estado"], "comments": "Carga inicial",
    }]}).json()
    return f"asociar: {resumen(asociar)} | estado: {resumen(estado)}"


def resumen(respuesta: dict) -> str:
    datos = respuesta.get("data")
    if isinstance(datos, list) and datos:
        return datos[0].get("code", str(datos[0]))
    return str(respuesta)


if __name__ == "__main__":
    zoho = conectar()
    plan = preparar_plan(zoho)

    incompletos = [p for p in plan if not p["candidato_id"] or not p["vacante_id"]]
    for p in incompletos:
        falta = "candidato" if not p["candidato_id"] else "vacante"
        print(f"AVISO: no encuentro en Zoho el {falta} de {p['nombre']} ({p['puesto']}). Lo salto.")
    listos = [p for p in plan if p not in incompletos]

    if "--todos" in sys.argv:
        elegidos = listos
    elif "--uno" in sys.argv:
        elegidos = listos[:1]
    else:
        for p in listos:
            print(f"{p['nombre']:<26} -> {p['puesto']:<18} estado {p['estado']}")
        print(f"\n{len(listos)} candidatos listos. No se ha cambiado nada en Zoho.")
        print("Para probar con uno: python cargar_en_zoho.py --uno")
        sys.exit()

    for p in elegidos:
        print(f"{p['nombre']} -> {p['puesto']} ({p['estado']}): {aplicar(zoho, p)}")
