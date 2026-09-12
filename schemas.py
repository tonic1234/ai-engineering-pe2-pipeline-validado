"""schemas.py — Contrato de salida del pipeline de extracción.

APUNTE DE CLASE:
La consigna pide tres campos: tecnologías, nivel de criticidad y resumen técnico.
Lo importante no es solo "que estén", sino las RESTRICCIONES semánticas de negocio:
que la lista de tecnologías no venga vacía (min_length=1) y que el resumen tenga un
mínimo de caracteres razonable. Eso es la validación semántica, la única de las tres
(sintáctica / estructural / semántica) que no te regala el framework.

Elegí Enum para la criticidad porque así el modelo no puede inventar valores raros
tipo "media-alta" o "crítico".
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class ExtraccionTecnica(BaseModel):
    """Lo que debe devolver el pipeline para cualquier texto de entrada."""

    tecnologias: list[str] = Field(
        min_length=1,
        description="Tecnologías o componentes técnicos mencionados en el texto",
    )
    nivel_de_criticidad: NivelCriticidad = Field(
        description="Gravedad del problema o criticidad de la arquitectura descrita",
    )
    resumen_tecnico: str = Field(
        min_length=10,
        max_length=400,
        description="Resumen técnico: qué pasa y por qué importa",
    )
