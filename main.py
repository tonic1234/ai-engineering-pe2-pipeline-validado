"""main.py — Mini-script async de prueba del pipeline.

Corre el mismo texto contra los proveedores configurados para comprobar que el pipeline
es intercambiable, y después prueba un texto ambiguo (prueba de estrés).

Uso:
    cp .env.example .env   # completar la key del proveedor
    python main.py
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from chain import process_text

TEXTO_EJEMPLO = (
    "Nuestra API en FastAPI está devolviendo timeouts intermitentes. El caché en Redis "
    "parece saturarse en picos de tráfico y las conexiones a PostgreSQL se agotan porque "
    "el pool está mal dimensionado. Esto está afectando a usuarios en producción."
)

TEXTO_AMBIGUO = "El sistema anda medio raro últimamente, no sé bien qué está pasando."

PROVEEDORES = ["gemini"]  # para probar los tres: ["openai", "anthropic", "gemini"]


async def main() -> None:
    load_dotenv()

    for provider in PROVEEDORES:
        print(f"\n--- {provider.upper()} ---")
        try:
            resultado = await process_text(TEXTO_EJEMPLO, provider=provider)
            print(resultado.model_dump_json(indent=2))
        except Exception as exc:
            print(f"falló: {exc}")

    print("\n=== Prueba de estrés (texto ambiguo) ===")
    resultado = await process_text(TEXTO_AMBIGUO, provider=PROVEEDORES[0])
    print(resultado.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
