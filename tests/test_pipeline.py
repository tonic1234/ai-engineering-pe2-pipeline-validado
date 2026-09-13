"""tests/test_pipeline.py — Pruebas del pipeline de extracción.

APUNTE: acá me interesa probar dos cosas que puedo verificar sin llamar al LLM:
  1. Que el esquema Pydantic rechace lo que tiene que rechazar (validación semántica).
  2. Que la cadena esté armada como pide la consigna y que soporte los tres proveedores.

Correr:  pytest -q
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chain import PROMPT, build_chain, build_llm
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
# Prompt / cadena / proveedores
# --------------------------------------------------------------------------
def test_prompt_espera_la_variable_texto():
    assert "texto" in PROMPT.input_variables


def test_prompt_no_hardcodea_el_texto():
    system = PROMPT.messages[0].prompt.template
    assert "{texto}" not in system


def test_la_cadena_se_construye():
    cadena = build_chain()
    assert len(cadena.steps) == 2  # prompt | modelo-estructurado


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_build_llm_soporta_los_tres_proveedores(provider):
    assert build_llm(provider=provider) is not None


def test_build_llm_rechaza_proveedor_desconocido():
    with pytest.raises(ValueError):
        build_llm(provider="perplexity")
