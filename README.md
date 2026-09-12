# Pipeline de extracción de entidades técnicas

Pre-entrega 2 del curso **AI Engineering** (Coderhouse).
Recibe un texto técnico (una descripción de arquitectura o el log de un error) y devuelve
un objeto **validado** con las tecnologías mencionadas, el nivel de criticidad y un resumen.

## Qué hay adentro

| Archivo | Qué hace |
|---|---|
| `schemas.py` | `ExtraccionTecnica`: el contrato de salida (con restricciones de negocio). |
| `chain.py` | Cadena LCEL: `prompt | llm.with_structured_output(...)` + `.with_retry(...)`. |
| `main.py` | Script de prueba con un caso normal y un caso ambiguo. |
| `tests/` | Pruebas del esquema y de la estructura de la cadena. |

## Cómo correrlo

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # completar OPENAI_API_KEY
python main.py
```

## Variables de entorno

| Variable | Descripción |
|---|---|
| `OPENAI_API_KEY` | Requerida para que la cadena pueda llamar al modelo. |

## Ejemplo de salida

Entrada:

> El servicio de pagos está construido con FastAPI, usa Redis como caché y PostgreSQL
> como base de datos principal. Bajo carga alta se detectaron timeouts en las conexiones
> concurrentes y el p95 de latencia se triplicó.

Salida:

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "API con caché en Redis y persistencia en PostgreSQL; el cuello de botella está en las conexiones concurrentes bajo carga alta."
}
```

## Decisiones de diseño

- **Contrato primero**: las restricciones van en el esquema, no en el prompt. `tecnologias`
  tiene `min_length=1` y `nivel_de_criticidad` es un `Enum`, así que el modelo no puede
  devolver una criticidad inventada.
- **Prompt modular**: se usa `ChatPromptTemplate` con la variable `{texto}`. No hay
  f-strings de Python dentro de la cadena.
- **Salida estructurada**: `llm.with_structured_output(ExtraccionTecnica)` fuerza el formato
  (por debajo usa tool calling).
- **Resiliencia**: `.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)` reintenta
  errores transitorios (red, 429). No se reintentan errores permanentes.
- **Async**: `process_text()` usa `.ainvoke()` y loguea el resultado de la validación.

## Tests

```bash
pytest -q
```

Verifican el esquema (validación semántica) y la estructura de la cadena, sin llamar al
modelo.
