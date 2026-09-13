"""chain.py — Cadena LCEL con salida estructurada y resiliencia.

APUNTE DE CLASE:
La composición es literalmente esta:

    chain = (PROMPT | model.with_structured_output(EntidadesTecnicas)).with_retry(...)

Ese "|" es LCEL: cada eslabón recibe la salida del anterior. El prompt arma el
mensaje, el modelo genera, y with_structured_output() se encarga de que la respuesta
cumpla el esquema Pydantic (por debajo usa tool calling / JSON mode).

Tres cosas que el profe marcó como errores típicos y traté de evitar:
  1. NO usar f-strings para meter el texto en el prompt. Se declara la variable {texto}
     en el ChatPromptTemplate y LangChain la resuelve sola.
  2. Reintentar solo errores TRANSITORIOS. with_retry() sirve para un 429 o un corte de
     red; si el prompt está mal armado, reintentar no arregla nada.
  3. temperature=0 a propósito: para extracción estructurada queremos determinismo,
     no creatividad.

El modelo se elige con una fábrica (misma idea del Módulo 1): así la cadena es la misma
sin importar el proveedor.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from schemas import EntidadesTecnicas

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipeline_extraccion")

# Modelo por defecto de cada proveedor (reutilizo el criterio del Módulo 1).
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-flash-latest",  # el que tiene free tier, sin tarjeta
}

SYSTEM_PROMPT = (
    "Sos un analista técnico. Extraé información estructurada del texto que te pasa el "
    "usuario. Identificá las tecnologías o componentes mencionados, evaluá el nivel de "
    "criticidad del problema o de la arquitectura descrita, y generá un resumen técnico "
    "breve (1-2 oraciones) que explique qué pasa y por qué importa. Si el texto es "
    "ambiguo, elegí la interpretación más razonable y no dejes campos vacíos."
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{texto}"),
    ]
)


def get_model(provider: str | None = None, model: str | None = None, temperature: float = 0.0):
    """Fábrica de modelos: devuelve el modelo del proveedor pedido.

    Reutilizo la idea del Módulo 1: se elige por variable de entorno, así cambiar de
    proveedor no toca la cadena.
    """

    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    raise ValueError(f"Proveedor no soportado: {provider!r} (opciones: openai, anthropic, gemini)")


def build_chain(provider: str | None = None, model: str | None = None, temperature: float = 0.0):
    """Devuelve la cadena prompt | modelo-con-salida-estructurada, con reintentos."""

    llm = get_model(provider=provider, model=model, temperature=temperature)

    # El contrato: el modelo DEBE devolver algo que valide contra EntidadesTecnicas.
    structured_model = llm.with_structured_output(EntidadesTecnicas)

    # Resiliencia para errores transitorios (red, 429): 3 intentos con backoff + jitter.
    chain = (PROMPT | structured_model).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )
    return chain


@lru_cache(maxsize=2)
def get_chain(provider: str | None = None):
    """Devuelve la cadena ya construida (una sola vez por proveedor).

    Antes la construía al importar el módulo, pero eso exigía tener la API key ya
    cargada en ese momento y rompía los tests. Mejor construirla la primera vez que se
    usa de verdad.
    """

    return build_chain(provider=provider)


async def process_text(text: str, provider: str | None = None) -> EntidadesTecnicas:
    """Ejecuta la cadena de forma asíncrona y loguea el resultado de la validación."""

    if not text or not text.strip():
        raise ValueError("El texto de entrada está vacío")

    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    logger.info("[%s] Procesando texto (%d caracteres)...", provider, len(text))

    try:
        resultado: EntidadesTecnicas = await get_chain(provider).ainvoke({"texto": text})
    except Exception as exc:
        # Ojo: acá se cae después de agotar los 3 reintentos. Lo logueamos con el tipo
        # de error para poder distinguir un problema transitorio de uno de formato.
        logger.error("[%s] Falló tras reintentos: %s (%s)", provider, exc, type(exc).__name__)
        raise

    logger.info("[%s] Extracción validada: %s", provider, resultado.model_dump())
    return resultado
