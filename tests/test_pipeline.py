"""tests/test_pipeline.py — Pruebas del pipeline de extracción.

APUNTE: acá me interesa probar lo que puedo verificar sin llamar al LLM:
  1. Que el esquema Pydantic rechace lo que tiene que rechazar y LIMPIE lo que debe
     limpiar (validación semántica + el field_validator propio).
  2. Que la cadena esté armada como pide la consigna y que soporte los tres proveedores.

Correr:  pytest -q
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chain import PROMPT, build_chain, get_model
from schemas import EntidadesTecnicas, NivelCriticidad


# --------------------------------------------------------------------------
# Esquema / validación
# --------------------------------------------------------------------------
def test_extraccion_valida():
    data = EntidadesTecnicas(
        tecnologias=["FastAPI", "Redis"],
        nivel_de_criticidad="alta",
        resumen_tecnico="API con caché y persistencia; el cuello de botella está en las conexiones concurrentes.",
    )
    assert data.nivel_de_criticidad is NivelCriticidad.ALTA


def test_lista_de_tecnologias_vacia_falla():
    with pytest.raises(ValidationError):
        EntidadesTecnicas(tecnologias=[], nivel_de_criticidad="baja", resumen_tecnico="x" * 20)


def test_criticidad_inventada_falla():
    with pytest.raises(ValidationError):
        EntidadesTecnicas(
            tecnologias=["Docker"],
            nivel_de_criticidad="altísima",  # no está en el enum
            resumen_tecnico="x" * 20,
        )


def test_resumen_demasiado_corto_falla():
    with pytest.raises(ValidationError):
        EntidadesTecnicas(tecnologias=["Nginx"], nivel_de_criticidad="media", resumen_tecnico="corto")


def test_lista_se_limpia_y_deduplica():
    # Este es el validador propio: saca espacios, descarta vacíos y deduplica.
    data = EntidadesTecnicas(
        tecnologias=["  FastAPI ", "FastAPI", "", "Redis  "],
        nivel_de_criticidad="media",
        resumen_tecnico="resumen suficientemente largo",
    )
    assert data.tecnologias == ["FastAPI", "Redis"]


def test_lista_solo_con_vacios_falla():
    with pytest.raises(ValidationError):
        EntidadesTecnicas(
            tecnologias=["   ", ""],
            nivel_de_criticidad="baja",
            resumen_tecnico="resumen suficientemente largo",
        )


# --------------------------------------------------------------------------
# Prompt / cadena / proveedores
# --------------------------------------------------------------------------
def test_prompt_espera_la_variable_texto():
    assert "texto" in PROMPT.input_variables


def test_prompt_no_hardcodea_el_texto():
    system = PROMPT.messages[0].prompt.template
    assert "{texto}" not in system


def test_la_cadena_se_construye():
    from langchain_core.runnables import RunnableSequence

    cadena = build_chain()
    # La cadena queda envuelta en el retry, así que la secuencia está en .bound.
    secuencia = cadena.bound if hasattr(cadena, "bound") else cadena
    assert isinstance(secuencia, RunnableSequence)
    assert secuencia.steps[0] is PROMPT  # primer eslabón: el prompt


def test_usa_temperature_cero():
    # Para extracción estructurada queremos determinismo.
    modelo = get_model(provider="gemini")
    assert modelo.temperature == 0


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_get_model_soporta_los_tres_proveedores(provider):
    assert get_model(provider=provider) is not None


def test_get_model_rechaza_proveedor_desconocido():
    with pytest.raises(ValueError):
        get_model(provider="perplexity")
