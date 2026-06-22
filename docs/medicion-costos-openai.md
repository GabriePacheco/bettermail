# Medicion de costos de OpenAI

## Que mide BetterMail AI

Cada respuesta exitosa usa los conteos entregados por OpenAI:

- Tokens de entrada.
- Tokens de entrada cacheados.
- Tokens de salida.
- Tokens totales.
- Modelo que genero la respuesta.

El costo estimado se calcula asi:

```text
entrada no cacheada * tarifa de entrada
+ entrada cacheada * tarifa cacheada
+ salida * tarifa de salida
```

Las tarifas se expresan en USD por un millon de tokens y se configuran mediante variables de entorno. Los valores iniciales del proyecto corresponden a `gpt-4.1-mini`: entrada `0.40`, entrada cacheada `0.10` y salida `1.60` USD por millon de tokens.

Fuentes oficiales:

- https://openai.com/api/pricing/
- https://platform.openai.com/usage

Antes de cambiar `MODEL_NAME`, confirma las tarifas oficiales y actualiza:

```env
OPENAI_INPUT_COST_PER_1M_USD=0.40
OPENAI_CACHED_INPUT_COST_PER_1M_USD=0.10
OPENAI_OUTPUT_COST_PER_1M_USD=1.60
OPENAI_PRICING_LABEL=gpt-4.1-mini-2026-06
```

## Donde se guarda

- `usage_logs`: detalle por solicitud, sin almacenar el contenido del correo.
- `operational_metrics/openai_YYYY-MM-DD`: agregado diario sin datos personales.

Los agregados incluyen solicitudes, tokens y costo estimado. El panel de OpenAI sigue siendo la fuente final de facturacion porque puede incluir ajustes, creditos e impuestos.

## Consultar

Abre `https://bettermailai.web.app/internal-admin`, pega la clave administrativa y pulsa **Consultar** en **Costo de OpenAI**.

La API protegida equivalente es:

```http
GET /billing/admin/openai-costs?days=30
X-Admin-Secret: <clave privada>
```

La medicion comienza al desplegar esta version. Las llamadas historicas anteriores no se pueden reconstruir con precision porque no guardaban los tokens reportados por OpenAI.

