"""Comprueba qué puede hacer en Zoho cada juego de llaves, sin cambiar nada.

Uso:  python comprobar_permisos.py

Las lecturas piden un solo registro. Las escrituras se prueban con datos
vacíos o con un id que no existe: Zoho primero mira si las llaves tienen
permiso y, si lo tienen, rechaza los datos, así que nunca se modifica nada.
"""
from pathlib import Path

import httpx
from dotenv import dotenv_values

LLAVES = dotenv_values(Path(__file__).parent / ".env")
URL_TOKEN = "https://accounts.zoho.eu/oauth/v2/token"
URL_API = "https://recruit.zoho.eu/recruit/v2"

JUEGOS = {
    "Llaves de carga (ZOHO_REFRESH_TOKEN)": "ZOHO_REFRESH_TOKEN",
    "Llaves del servidor (ZOHO_REFRESH_TOKEN_SERVIDOR)": "ZOHO_REFRESH_TOKEN_SERVIDOR",
}

PRUEBAS = [
    ("Leer candidaturas", "GET", "/Applications", {"params": {"per_page": 1}}),
    ("Leer fichas de candidatos", "GET", "/Candidates", {"params": {"per_page": 1}}),
    ("Leer vacantes", "GET", "/JobOpenings", {"params": {"per_page": 1}}),
    ("Cambiar estado de un candidato", "PUT", "/Candidates/status", {"json": {"data": []}}),
    ("Editar vacantes", "PUT", "/JobOpenings", {"json": {"data": []}}),
    ("Borrar candidatos", "DELETE", "/Candidates", {"params": {"ids": "1"}}),
]


def cliente(variable: str) -> httpx.Client:
    token = httpx.post(URL_TOKEN, data={
        "grant_type": "refresh_token",
        "client_id": LLAVES["ZOHO_CLIENT_ID"],
        "client_secret": LLAVES["ZOHO_CLIENT_SECRET"],
        "refresh_token": LLAVES[variable],
    }).json()["access_token"]
    return httpx.Client(base_url=URL_API, headers={"Authorization": f"Zoho-oauthtoken {token}"}, timeout=30)


def tiene_permiso(respuesta: httpx.Response) -> bool:
    # Sin permiso, Zoho responde OAUTH_SCOPE_MISMATCH. Cualquier otra respuesta
    # (datos, o "datos no válidos" en las escrituras) significa que sí lo tiene.
    return "OAUTH_SCOPE_MISMATCH" not in respuesta.text


if __name__ == "__main__":
    for titulo, variable in JUEGOS.items():
        if not LLAVES.get(variable):
            print(f"\n{titulo}: no está en .env, la salto.")
            continue
        print(f"\n{titulo}:")
        with cliente(variable) as zoho:
            for nombre, metodo, ruta, opciones in PRUEBAS:
                respuesta = zoho.request(metodo, ruta, **opciones)
                print(f"  {nombre:.<34} {'SÍ' if tiene_permiso(respuesta) else 'NO'}")
    print("\nNo se ha cambiado nada en Zoho.")
