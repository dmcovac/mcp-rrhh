from fastmcp import FastMCP

servidor = FastMCP("rrhh")

CANDIDATOS = [
    {"nombre": "Ana Ruiz", "puesto": "Data Engineer", "fase": "Entrevista técnica"},
    {"nombre": "Luis Marín", "puesto": "Data Engineer", "fase": "Criba curricular"},
    {"nombre": "Sara Gil", "puesto": "Consultor MDM", "fase": "Oferta enviada"},
    {"nombre": "Marc Soler", "puesto": "Consultor MDM", "fase": "Entrevista RRHH"},
    {"nombre": "Nadia Haddad", "puesto": "Project Manager", "fase": "Descartado"},
]


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

if __name__ == "__main__":
    servidor.run()