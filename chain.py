"""chain.py — Cadena LCEL con salida estructurada y resiliencia.

APUNTE DE CLASE:
La composición es literalmente esta:

    chain = PROMPT | llm.with_structured_output(ExtraccionTecnica)

Ese "|" es LCEL: cada eslabón recibe la salida del anterior. El prompt arma el
mensaje, el modelo genera, y with_structured_output() se encarga de que la respuesta
cumpla el esquema Pydantic (por debajo usa tool calling / JSON mode).

Dos cosas que el profe marcó como errores típicos y traté de evitar:
  1. NO usar f-strings para meter el texto en el prompt. Se declara la variable {texto}
     en el ChatPromptTemplate y LangChain la resuelve sola.
  2. Reintentar solo errores TRANSITORIOS. with_retry() sirve para un 429 o un corte de
     red; si el prompt está mal armado, reintentar no arregla nada.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from schemas import ExtraccionTecnica

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Modelo por defecto de cada proveedor (reutilizo el criterio del Módulo 1).
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-flash-latest",  # el que tiene free tier, sin tarjeta
}

SYSTEM_PROMPT = (
    "Sos un arquitecto de software senior. A partir de un texto técnico (una "
    "descripción de arquitectura o el log de un error), extraé: 1) las tecnologías o "
    "componentes mencionados, 2) el nivel de criticidad (baja, media o alta) según la "
    "gravedad de lo que se describe, y 3) un resumen técnico conciso (máximo 40 "
    "palabras) que explique qué pasa y por qué importa. Si el texto es ambiguo, elegí "
    "la interpretación más razonable y no dejes campos vacíos."
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Texto a analizar:\n{texto}"),
    ]
)


def build_llm(provider: str | None = None, model: str | None = None, temperature: float = 0.0):
    """Devuelve el modelo del proveedor elegido.

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


def build_chain(model: str | None = None, temperature: float = 0.0):
    """Devuelve la cadena prompt | modelo-con-salida-estructurada-con-retry."""

    llm = build_llm(model=model, temperature=temperature)  # 0 = determinista

    # El contrato: el modelo DEBE devolver algo que valide contra ExtraccionTecnica.
    structured = llm.with_structured_output(ExtraccionTecnica)

    # Resiliencia para errores transitorios (red, 429): 3 intentos con backoff + jitter.
    resilient = structured.with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    return PROMPT | resilient


@lru_cache(maxsize=1)
def get_chain():
    """Devuelve la cadena ya construida (una sola vez).

    Antes la construía al importar el módulo, pero eso exigía tener la API key ya
    cargada en ese momento y rompía los tests. Mejor construirla la primera vez que se
    usa de verdad.
    """

    return build_chain()


async def process_text(text: str) -> ExtraccionTecnica:
    """Ejecuta la cadena de forma asíncrona y loguea el resultado de la validación."""

    if not text or not text.strip():
        raise ValueError("El texto de entrada está vacío")

    logger.info("Procesando texto (%d caracteres)", len(text))
    try:
        resultado: ExtraccionTecnica = await get_chain().ainvoke({"texto": text})
    except Exception as exc:
        # Ojo: acá se cae después de agotar los 3 reintentos. Lo logueamos con el tipo
        # de error para poder distinguir un problema transitorio de uno de formato.
        logger.error("El pipeline falló tras los reintentos: %s (%s)", exc, type(exc).__name__)
        raise

    logger.info(
        "Validación OK -> tecnologías=%s criticidad=%s",
        resultado.tecnologias,
        resultado.nivel_de_criticidad.value,
    )
    return resultado
