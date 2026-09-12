"""main.py — Mini-script async de prueba del pipeline.

Uso:
    cp .env.example .env   # completar OPENAI_API_KEY
    python main.py
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from chain import process_text

TEXTO_EJEMPLO = (
    "El servicio de pagos está construido con FastAPI, usa Redis como caché y "
    "PostgreSQL como base de datos principal. Bajo carga alta se detectaron timeouts "
    "en las conexiones concurrentes y el p95 de latencia se triplicó."
)

TEXTO_AMBIGUO = "Hubo un problema en producción y tardó más de lo normal."


async def main() -> None:
    load_dotenv()

    for etiqueta, texto in (("caso normal", TEXTO_EJEMPLO), ("caso ambiguo", TEXTO_AMBIGUO)):
        print(f"\n=== {etiqueta} ===")
        resultado = await process_text(texto)
        print(resultado.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
