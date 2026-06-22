from openai import OpenAI
from app.config import get_settings


TONE_MAP = {
    "profesional": "profesional, claro, respetuoso y natural",
    "firme_amable": "serio, firme, amable y con autoridad, sin sonar agresivo",
    "ejecutivo": "ejecutivo, directo, elegante y estrategico",
    "conciliador": "cordial, conciliador, prudente y constructivo",
    "directo": "directo, breve, claro y sin rodeos innecesarios",
    "diplomatico": "diplomatico, cuidadoso, elegante y profesional",
    "institucional": "formal, institucional, sobrio y preciso",
    "reclamo_formal": "formal, firme, claro y orientado a dejar constancia sin perder profesionalismo",
}


def get_client():
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def build_user_prompt(text: str, tone_description: str, mode: str, context: str | None):
    if mode == "suggest_reply":
        return f"""
Genera una respuesta profesional usando el contexto del correo anterior.

Reglas obligatorias:
- No inventes datos.
- No agregues compromisos que el usuario no haya indicado.
- Se claro, natural y breve.
- Manten el idioma del contexto.
- Usa un tono: {tone_description}.
- Si el contexto contiene enojo, insultos o agresividad verbal no fisica, responde con una version profesional, firme, respetuosa y segura.
- No incluyas amenazas, violencia, insultos, acoso, crimen ni acusaciones legales no sustentadas.
- Devuelve unicamente la respuesta sugerida, sin explicaciones, sin markdown y sin comillas.
-Ten en mente un correo completo, con saludo, cuerpo y despedida, aunque el texto original solo tenga el cuerpo del correo.

Contexto del correo anterior:
\"\"\"
{context or ""}
\"\"\"
""".strip()

    return f"""
Reescribe unicamente el texto proporcionado por el usuario.

Reglas obligatorias:
- No cambies el sentido original.
- No inventes informacion.
- No respondas al historial del correo.
- No incluyas cabeceras.
- No agregues fechas, nombres, compromisos ni datos que no existan.
- No elimines datos importantes.
- Conserva nombres, valores, fechas, cargos, lugares y detalles.
- Conserva la estructura visual del texto original.
- Mantén saludo, cuerpo, listas, fechas, instrucciones y despedida en bloques separados si ya estaban separados.
- No unas en un solo párrafo líneas o párrafos que el usuario escribió separados.
- Respeta saltos de línea significativos y listas de una línea por elemento.
- Manten el idioma original.
- Usa un tono: {tone_description}.
- Si el texto expresa enojo, insultos, frustracion o agresividad verbal no fisica, transformalo en un mensaje profesional, firme, respetuoso y seguro.
- Mantén la intencion comunicativa razonable: desacuerdo, reclamo, limite, solicitud de respuesta, advertencia formal o cierre de conversacion.
- No conserves amenazas, lenguaje violento, insultos ni expresiones humillantes.
- No amplifiques el conflicto ni agregues dano fisico, acoso, crimen o intimidacion.
- No hagas acusaciones legales no sustentadas.
- Si el usuario pide conservar o ejecutar dano real, crimen, acoso dirigido o amenaza directa, rechaza brevemente y ofrece una alternativa profesional segura.
- Devuelve unicamente el texto reescrito, sin explicaciones, sin markdown y sin comillas.
-Ten en mente un correo completo, con saludo, cuerpo y despedida, aunque el texto original solo tenga el cuerpo del correo.

Texto original:
\"\"\"
{text}
\"\"\"
""".strip()


def rewrite_email_text(
    text: str,
    tone: str,
    mode: str = "rewrite_draft",
    context: str | None = None,
):
    settings = get_settings()
    client = get_client()
    normalized_mode = mode or "rewrite_draft"
    tone_description = TONE_MAP.get(tone, TONE_MAP["profesional"])

    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres BetterMail AI, un asistente experto en correos profesionales. "
                    "Tu objetivo es mejorar claridad, ortografia, estructura y tono sin cambiar el sentido original. "
                    "Cuando el usuario escriba con enojo o agresividad verbal no fisica, convierte el mensaje "
                    "en comunicacion profesional, firme y respetuosa sin conservar amenazas ni insultos."
                ),
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    text=text,
                    tone_description=tone_description,
                    mode=normalized_mode,
                    context=context,
                ),
            },
        ],
        temperature=0.5,
    )

    rewritten_text = response.choices[0].message.content

    if not rewritten_text:
        raise ValueError("OpenAI no devolvio contenido.")

    return rewritten_text.strip()
