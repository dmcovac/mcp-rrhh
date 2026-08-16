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


if __name__ == "__main__":
    servidor.run()