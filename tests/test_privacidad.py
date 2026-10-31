"""Pruebas deterministas de la capa de privacidad.

No usan Zoho ni la API de Claude: se sustituyen por datos falsos fijos.
Por eso dan siempre el mismo resultado, no cuestan nada y no envían datos
a nadie (decisión 7 de la memoria: tests deterministas en vez de un LLM juez).

Ejecutar:  python -m pytest -v
"""

import asyncio
import csv
import json

import pytest
from fastmcp import Client

import agente
import servidor_rrhh

# Candidaturas falsas con TODOS los datos sensibles que Zoho podría enviar.
CANDIDATURAS = [
    {"$Candidate_Id": "111", "$Job_Opening_Id": "J1", "Full_Name": "Ana Prueba Uno",
     "Posting_Title": "Data Engineer", "Application_Status": "Entrevista programada",
     "Email": "ana.prueba@example.com", "Mobile": "+34 600 111 111", "Expected_Salary": 41234,
     "Street": "Calle Inventada 12", "Additional_Info": "Llamar por la tarde al 600111111"},
    {"$Candidate_Id": "222", "$Job_Opening_Id": "J1", "Full_Name": "Bruno Prueba Dos",
     "Posting_Title": "Data Engineer", "Application_Status": "Rechazado",
     "Email": "bruno.prueba@example.com", "Mobile": "+34 600 222 222", "Expected_Salary": 38999,
     "Street": "Avenida Ficticia 34", "Additional_Info": "Prefiere trabajo en remoto"},
    {"$Candidate_Id": "333", "$Job_Opening_Id": "J2", "Full_Name": "Carla Prueba Tres",
     "Posting_Title": "Consultor MDM", "Application_Status": "En revisión",
     "Email": "carla.prueba@example.com", "Mobile": "+34 600 333 333", "Expected_Salary": 52500,
     "Street": "Plaza Imaginaria 5", "Additional_Info": "Recomendada por un empleado"},
]
SENSIBLES = [v for c in CANDIDATURAS for k, v in c.items()
             if k in {"Full_Name", "Email", "Mobile", "Expected_Salary", "Street", "Additional_Info"}]
SENSIBLES += [p for c in CANDIDATURAS for p in c["Full_Name"].split()]  # nombre o apellido sueltos


@pytest.fixture(autouse=True)
def entorno_falso(tmp_path, monkeypatch):
    """Cada prueba usa datos falsos y archivos temporales; nunca toca Zoho."""
    monkeypatch.setattr(servidor_rrhh, "leer_candidaturas", lambda: CANDIDATURAS)
    monkeypatch.setattr(servidor_rrhh, "REGISTRO", tmp_path / "registro.csv")
    monkeypatch.setattr(servidor_rrhh, "CODIGOS", tmp_path / "codigos.json")

    def zoho_prohibido():
        raise AssertionError("La prueba ha intentado escribir en Zoho")
    monkeypatch.setattr(servidor_rrhh, "zoho", zoho_prohibido)
    monkeypatch.setattr(agente, "REGISTRO_DECISIONES", tmp_path / "decisiones.csv")
    return tmp_path


def llamar(herramienta, **argumentos) -> str:
    """Llama a la herramienta como lo haría la IA y devuelve TODO lo que recibiría
    (el texto y los datos estructurados), para buscar fugas en ambos."""
    async def _llamar():
        async with Client(servidor_rrhh.servidor) as cliente:
            resultado = await cliente.call_tool(herramienta, argumentos)
            texto = "\n".join(c.text for c in resultado.content if hasattr(c, "text"))
            return texto + "\n" + json.dumps(resultado.structured_content, ensure_ascii=False)
    return asyncio.run(_llamar())


def candidatos() -> list[dict]:
    """La lista de candidatos tal como la recibe la IA."""
    async def _llamar():
        async with Client(servidor_rrhh.servidor) as cliente:
            resultado = await cliente.call_tool("listar_candidatos", {})
            datos = resultado.structured_content
            return datos["result"] if isinstance(datos, dict) and "result" in datos else datos
    return asyncio.run(_llamar())


# 1. Ningún dato personal llega a la IA ---------------------------------------

@pytest.mark.parametrize("herramienta, argumentos", [
    ("listar_candidatos", {}),
    ("buscar_candidatos", {"puesto": "Data Engineer"}),
    ("buscar_candidatos", {"fase": "Rechazado"}),
])
def test_ningun_dato_personal_en_la_salida(herramienta, argumentos):
    texto = llamar(herramienta, **argumentos)
    for dato in SENSIBLES:
        assert str(dato) not in texto, f"'{dato}' ha llegado a la IA"


def test_solo_salen_codigo_puesto_y_fase():
    lista = candidatos()
    assert len(lista) == 3
    for candidato in lista:
        assert set(candidato) == {"codigo", "puesto", "fase"}
        assert candidato["codigo"].startswith("C-")


# 2. Los códigos son estables -------------------------------------------------

def test_mismo_candidato_mismo_codigo_entre_llamadas():
    primera = candidatos()
    segunda = candidatos()
    assert primera == segunda


def test_codigos_distintos_para_personas_distintas():
    codigos = [c["codigo"] for c in candidatos()]
    assert len(codigos) == len(set(codigos))


def test_la_tabla_de_codigos_queda_fuera_de_lo_que_ve_la_ia(entorno_falso):
    llamar("listar_candidatos")
    tabla = json.loads((entorno_falso / "codigos.json").read_text(encoding="utf-8"))
    assert {d["nombre"] for d in tabla.values()} == {c["Full_Name"] for c in CANDIDATURAS}


# 3. Escrituras: códigos sí, nombres no, y nada sin confirmar ------------------

def test_cambiar_fase_no_acepta_nombres():
    llamar("listar_candidatos")
    texto = llamar("cambiar_fase", codigo="Ana Prueba Uno", nueva_fase="Rechazado")
    assert "No existe ningún candidato" in texto


def test_cambiar_fase_sin_confirmar_no_escribe_y_no_revela_nombres():
    codigo = candidatos()[0]["codigo"]
    texto = llamar("cambiar_fase", codigo=codigo, nueva_fase="Rechazado")
    assert "pendiente_de_confirmacion" in texto
    assert codigo in texto
    for dato in SENSIBLES:
        assert str(dato) not in texto
    # Si hubiera intentado escribir, zoho_prohibido() habría hecho fallar la prueba.


def test_cambiar_fase_rechaza_fases_inventadas():
    codigo = candidatos()[0]["codigo"]
    texto = llamar("cambiar_fase", codigo=codigo, nueva_fase="Fichado", confirmar=True)
    assert "no es una fase válida" in texto


# 4. El hook del agente: una persona decide cada escritura --------------------

@pytest.mark.parametrize("respuesta", ["n", "no", "", "vale", "sii", "yes"])
def test_hook_bloquea_si_la_persona_no_dice_si(monkeypatch, respuesta):
    monkeypatch.setattr("builtins.input", lambda _: respuesta)
    bloqueo = agente.hook_antes_de_herramienta("cambiar_fase", {"codigo": "C-0001", "nueva_fase": "Rechazado", "confirmar": True})
    assert bloqueo is not None and "NO" in bloqueo


@pytest.mark.parametrize("respuesta", ["s", "si", "sí", "SI", " Sí "])
def test_hook_deja_pasar_con_un_si(monkeypatch, respuesta):
    monkeypatch.setattr("builtins.input", lambda _: respuesta)
    assert agente.hook_antes_de_herramienta("cambiar_fase", {"codigo": "C-0001", "nueva_fase": "Rechazado", "confirmar": True}) is None


@pytest.mark.parametrize("nombre, argumentos", [
    ("listar_candidatos", {}),
    ("buscar_candidatos", {"puesto": "Data Engineer"}),
    ("cambiar_fase", {"codigo": "C-0001", "nueva_fase": "Rechazado"}),  # vista previa, sin confirmar
])
def test_hook_no_molesta_en_lecturas_ni_en_vistas_previas(monkeypatch, nombre, argumentos):
    def no_preguntes(_):
        raise AssertionError("El hook ha preguntado sin motivo")
    monkeypatch.setattr("builtins.input", no_preguntes)
    assert agente.hook_antes_de_herramienta(nombre, argumentos) is None


def test_hook_registra_cada_decision_humana(monkeypatch, entorno_falso):
    escritura = {"codigo": "C-0001", "nueva_fase": "Rechazado", "confirmar": True}
    for respuesta in ["n", "si"]:
        monkeypatch.setattr("builtins.input", lambda _, r=respuesta: r)
        agente.hook_antes_de_herramienta("cambiar_fase", escritura)
    with open(entorno_falso / "decisiones.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert [f["decision"] for f in filas] == ["rechazado", "aprobado"]


# 5. Traza: cada consulta queda registrada -------------------------------------

def test_cada_llamada_deja_una_linea_en_el_registro(entorno_falso):
    llamar("listar_candidatos")
    llamar("buscar_candidatos", puesto="Consultor MDM")
    llamar("cambiar_fase", codigo="C-9999", nueva_fase="Rechazado")
    with open(entorno_falso / "registro.csv", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    assert [f["herramienta"] for f in filas] == ["listar_candidatos", "buscar_candidatos", "cambiar_fase"]
    assert all(f["fecha"] and f["se_devolvio"] for f in filas)
