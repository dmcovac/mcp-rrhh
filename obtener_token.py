"""Cambia el código temporal de Zoho por un refresh token y lo guarda en .env.

Se ejecuta una sola vez:  python obtener_token.py
Antes hay que haber rellenado ZOHO_CLIENT_ID y ZOHO_CLIENT_SECRET en .env.
El código se escribe sin que se vea en pantalla y nunca se muestra el token.
"""
import sys
from getpass import getpass
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

ARCHIVO_ENV = Path(__file__).parent / ".env"
URL_TOKEN = "https://accounts.zoho.eu/oauth/v2/token"
URL_API = "https://recruit.zoho.eu/recruit/v2"

llaves = dotenv_values(ARCHIVO_ENV)
if not llaves.get("ZOHO_CLIENT_ID") or not llaves.get("ZOHO_CLIENT_SECRET"):
    sys.exit("Falta ZOHO_CLIENT_ID o ZOHO_CLIENT_SECRET en .env. Rellénalos y vuelve a ejecutar.")

codigo = getpass("Pega el código de Zoho (no se verá al pegarlo) y pulsa Enter: ").strip()

respuesta = httpx.post(URL_TOKEN, data={
    "grant_type": "authorization_code",
    "client_id": llaves["ZOHO_CLIENT_ID"],
    "client_secret": llaves["ZOHO_CLIENT_SECRET"],
    "code": codigo,
}).json()

if "refresh_token" not in respuesta:
    sys.exit(f"Zoho no ha dado el token: {respuesta.get('error', respuesta)}. "
             "El código caduca a los pocos minutos: genera otro y vuelve a probar.")

set_key(ARCHIVO_ENV, "ZOHO_REFRESH_TOKEN", respuesta["refresh_token"], quote_mode="never")
print("Token guardado en .env.")

# Prueba: pedir a Zoho las vacantes, para comprobar que la conexión funciona.
vacantes = httpx.get(
    f"{URL_API}/JobOpenings",
    headers={"Authorization": f"Zoho-oauthtoken {respuesta['access_token']}"},
).json()
titulos = [v.get("Posting_Title") for v in vacantes.get("data", [])]
print(f"Conexión con Zoho correcta. Vacantes encontradas: {titulos}")
