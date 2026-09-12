"""conftest.py — Configuración común para los tests.

APUNTE: los tests no llaman a ningún modelo real, pero varias clases de LangChain
verifican que exista una API key al construirse. Le pongo una clave dummy para que no
falle el import; nunca se hace una llamada de red.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
