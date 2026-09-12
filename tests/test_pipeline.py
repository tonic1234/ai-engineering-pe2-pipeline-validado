"""tests/test_pipeline.py — Pruebas del pipeline de extracción.

APUNTE: acá me interesa probar dos cosas que puedo verificar sin llamar al LLM:
  1. Que el esquema Pydantic rechace lo que tiene que rechazar (validación semántica).
  2. Que la cadena esté armada como pide la consigna (LCEL + structured output + retry).

Para el punto 2 verifico la ESTRUCTURA de la cadena, no el texto que devuelve el
modelo (eso cambiaría en cada corrida y haría un test frágil).

Correr:  pytest -q
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chain import PROMPT, build_chain
from schemas import ExtraccionTecnica, NivelCriticidad


# --------------------------------------------------------------------------
# Esquema / validación
# --------------------------------------------------------------------------
def test_extraccion_valida():
    data = ExtraccionTecnica(
        tecnologias=["FastAPI", "Redis"],
        nivel_de_criticidad="alta",
        resumen_tecnico="API con caché y persistencia; el cuello de botella está en las conexiones concurrentes.",
    )
    assert data.nivel_de_criticidad is NivelCriticidad.ALTA


def test_lista_de_tecnologias_vacia_falla():
    with pytest.raises(ValidationError):
        ExtraccionTecnica(tecnologias=[], nivel_de_criticidad="baja", resumen_tecnico="x" * 20)


def test_criticidad_inventada_falla():
    with pytest.raises(ValidationError):
        ExtraccionTecnica(
            tecnologias=["Docker"],
            nivel_de_criticidad="altísima",  # no está en el enum
            resumen_tecnico="x" * 20,
        )


def test_resumen_demasiado_corto_falla():
    with pytest.raises(ValidationError):
        ExtraccionTecnica(tecnologias=["Nginx"], nivel_de_criticidad="media", resumen_tecnico="corto")


# --------------------------------------------------------------------------
# Prompt / cadena
# --------------------------------------------------------------------------
def test_prompt_espera_la_variable_texto():
    assert "texto" in PROMPT.input_variables


def test_prompt_no_hardcodea_el_texto():
    # El system prompt no debe contener el texto de entrada: eso lo resuelve LangChain.
    system = PROMPT.messages[0].prompt.template
    assert "{texto}" not in system


def test_la_cadena_se_construye(monkeypatch):
    # build_chain() instancia ChatOpenAI; le damos una key dummy para que no falle
    # por entorno. No se hace ninguna llamada de red.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cadena = build_chain()
    assert len(cadena.steps) == 2  # prompt | modelo-estructurado
