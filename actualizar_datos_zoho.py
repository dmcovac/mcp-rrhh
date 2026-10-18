"""Rellena en Zoho Recruit el móvil, la dirección y el salario actual de cada
candidato, con los datos (falsos) de candidatos_zoho.csv.

Igual que cargar_en_zoho.py, primero enseña y después actúa:
  python actualizar_datos_zoho.py          solo muestra lo que haría, no cambia nada
  python actualizar_datos_zoho.py --uno    lo hace con el primer candidato, para revisarlo en Zoho
  python actualizar_datos_zoho.py --todos  lo hace con todos
"""
import csv
import sys

from cargar_en_zoho import ARCHIVO_CSV, conectar

# Columna del CSV -> campo de Zoho.
CAMPOS = {
    "Mobile": "Mobile",
    "Street": "Street",
    "Postal Code": "Zip_Code",
    "City": "City",
    "Province": "State",
    "Country": "Country",
    "Current Salary": "Current_Salary",
}

if __name__ == "__main__":
    zoho = conectar()
    candidatos_zoho = zoho.get("/Candidates", params={"per_page": 200}).json().get("data", [])
    id_por_email = {c["Email"].lower(): c["id"] for c in candidatos_zoho if c.get("Email")}

    with open(ARCHIVO_CSV, encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))

    plan = []
    for fila in filas:
        candidato_id = id_por_email.get(fila["Email"].lower())
        if not candidato_id:
            print(f"AVISO: no encuentro en Zoho a {fila['First Name']} {fila['Last Name']}. Lo salto.")
            continue
        datos = {campo: fila[columna] for columna, campo in CAMPOS.items()}
        datos["Current_Salary"] = float(datos["Current_Salary"])
        plan.append({"id": candidato_id, "nombre": f"{fila['First Name']} {fila['Last Name']}", **datos})

    if "--todos" in sys.argv:
        elegidos = plan
    elif "--uno" in sys.argv:
        elegidos = plan[:1]
    else:
        for p in plan:
            print(f"{p['nombre']:<26} {p['Mobile']}  {p['City']:<20} {p['Current_Salary']:>9.0f} €")
        print(f"\n{len(plan)} candidatos listos. No se ha cambiado nada en Zoho.")
        print("Para probar con uno: python actualizar_datos_zoho.py --uno")
        sys.exit()

    # Zoho acepta hasta 100 registros por llamada.
    datos = [{k: v for k, v in p.items() if k != "nombre"} for p in elegidos]
    respuesta = zoho.put("/Candidates", json={"data": datos}).json()
    for p, r in zip(elegidos, respuesta.get("data", [])):
        print(f"{p['nombre']}: {r.get('code')}")
