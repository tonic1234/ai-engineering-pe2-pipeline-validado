"""schemas.py — Contrato de salida del pipeline de extracción.

APUNTE DE CLASE:
La consigna pide tres campos: tecnologías, nivel de criticidad y resumen técnico.
Lo importante no es solo "que estén", sino las RESTRICCIONES semánticas de negocio:
que la lista de tecnologías no venga vacía (min_length=1) y que el resumen tenga un
mínimo de caracteres razonable. Esa es la validación semántica, la única de las tres
(sintáctica / estructural / semántica) que no te regala el framework.

Extra que agregué al repasar el tema: un field_validator propio para
limpiar la lista de tecnologías (sacar espacios, descartar vacíos y eliminar
duplicados). Recordé que dict.fromkeys preserva el ORDEN y deduplica a la vez, que es
justo lo que quería.

Elegí Enum para la criticidad porque así el modelo no puede inventar valores raros
tipo "media-alta" o "crítico".
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EntidadesTecnicas(BaseModel):
    """Lo que debe devolver el pipeline para cualquier texto de entrada."""

    tecnologias: List[str] = Field(
        min_length=1,
        description="Tecnologías, frameworks o herramientas mencionadas en el texto",
    )
    nivel_de_criticidad: NivelCriticidad = Field(
        description="Gravedad del problema o criticidad de la arquitectura descrita",
    )
    resumen_tecnico: str = Field(
        min_length=10,
        description="Resumen técnico de 1-2 oraciones sobre el contenido del texto",
    )

    @field_validator("tecnologias")
    @classmethod
    def sin_duplicados_ni_vacios(cls, v: List[str]) -> List[str]:
        """Limpia la lista: saca espacios, descarta vacíos y deduplica (manteniendo el orden)."""

        limpio = [t.strip() for t in v if t.strip()]
        if not limpio:
            raise ValueError("La lista de tecnologías no puede quedar vacía tras limpiar")
        return list(dict.fromkeys(limpio))


# Alias: el nombre que le había puesto al principio. Lo dejo para no romper imports.
ExtraccionTecnica = EntidadesTecnicas
