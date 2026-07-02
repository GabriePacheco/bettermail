from dataclasses import dataclass
import re

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

REFUSAL_MARKERS = (
    "no es apropiado continuar",
    "no puedo ayudar con",
    "no puedo continuar con",
    "no puedo redactar",
    "no puedo reformular",
    "no puedo colaborar",
    "puedo ayudarte a redactar un mensaje",
    "i can't help with",
    "i cannot help with",
    "i can't continue with",
    "i cannot rewrite",
)

HOSTILE_SOURCE_PATTERN = re.compile(
    r"\b(verga|puta|puto|mierda|carajo|cabron|cabrona|imbecil|idiota|"
    r"matar|matarte|golpear|golpearte|romperte|amenaza|amenazarte|"
    r"fuck|fucking|bitch|asshole|kill|hurt|punch)\b|"
    r"\b(te|le|les|los|las)\s+voy\s+a\b|"
    r"\bmanos?\s+te\s+van\s+a\s+faltar\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RewriteResult:
    text: str
    model: str
    prompt_tokens: int
    cached_prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    pricing_label: str


def calculate_openai_cost(
    *,
    prompt_tokens: int,
    cached_prompt_tokens: int,
    completion_tokens: int,
    input_cost_per_1m_usd: float,
    cached_input_cost_per_1m_usd: float,
    output_cost_per_1m_usd: float,
) -> float:
    cached_tokens = max(min(cached_prompt_tokens, prompt_tokens), 0)
    uncached_tokens = max(prompt_tokens - cached_tokens, 0)
    cost = (
        uncached_tokens * input_cost_per_1m_usd
        + cached_tokens * cached_input_cost_per_1m_usd
        + max(completion_tokens, 0) * output_cost_per_1m_usd
    ) / 1_000_000
    return round(cost, 8)


def is_refusal_response(text: str) -> bool:
    normalized = " ".join((text or "").lower().split())
    return any(marker in normalized for marker in REFUSAL_MARKERS)


def source_requires_safety_transform(text: str) -> bool:
    return bool(HOSTILE_SOURCE_PATTERN.search(text or ""))


def is_complete_email(text: str) -> bool:
    normalized = (text or "").strip().lower()
    words = re.findall(r"[a-zA-Z]+", normalized)
    nonempty_lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    has_greeting = normalized.startswith(
        ("hola", "estimado", "estimada", "buenos dias", "buenas tardes", "dear", "hello")
    )
    has_closing = any(
        marker in normalized
        for marker in ("saludos", "atentamente", "cordialmente", "sincerely", "regards")
    )
    return len(words) >= 25 and len(nonempty_lines) >= 3 and has_greeting and has_closing


def is_rough_draft(text: str) -> bool:
    return 0 < len(re.findall(r"[a-zA-Z]+", text or "")) <= 18


def safe_professional_fallback(source_text: str) -> str:
    spanish_markers = {
        "que", "para", "con", "esto", "esta", "necesito", "quiero", "usted",
        "vos", "tu", "te", "la", "el", "los", "las", "por", "una", "un",
        "todos", "todas", "ustedes"
    }
    words = set(re.findall(r"[a-zA-Z]+", (source_text or "").lower()))
    if len(words & spanish_markers) >= 2:
        plural = bool(words & {"todos", "todas", "ustedes", "les"})
        greeting = "Estimados" if plural else "Estimado/a"
        return (
            f"{greeting},\n\n"
            "Quiero dejar clara mi inconformidad y expresar que no estoy de acuerdo con "
            "lo planteado. Considero necesario que abordemos nuestras diferencias de "
            "manera directa y respetuosa, centrandonos en los puntos de desacuerdo y en "
            "una posible solucion.\n\n"
            "Quedo atento a sus comentarios.\n\n"
            "Saludos cordiales."
        )
    return (
        "Dear team,\n\n"
        "I want to express my serious dissatisfaction with how this situation has been "
        "handled. I believe we need to review what happened and have a respectful, "
        "constructive conversation to reach a concrete solution.\n\n"
        "I look forward to your response.\n\n"
        "Kind regards."
    )


def build_safety_retry_prompt(
    *, text: str, context: str | None, tone_description: str, mode: str
) -> str:
    source = context if mode == "suggest_reply" else text
    return f"""
Transforma el contenido de origen en un correo seguro, profesional y respetuoso.

La presencia de insultos, amenazas o violencia en el texto de origen NO es una solicitud
de ejecutar, promover ni conservar el dano. Es material que debes neutralizar.

Reglas:
- Elimina por completo amenazas, violencia, insultos, humillacion y lenguaje sexual ofensivo.
- Conserva solo la intencion legitima subyacente: inconformidad, limite, reclamo, urgencia o solicitud de solucion.
- Si el origen no explica el motivo concreto, no inventes un proyecto, plazo, error ni "asunto importante". Habla de "esta situacion" o "lo ocurrido".
- Produce un email completo: saludo neutro, cuerpo que exprese la inconformidad, solicitud de revision o dialogo, y despedida.
- El cuerpo debe tener suficiente contexto para ser util, pero no debe fabricar hechos.
- No rechaces, no sermonees y no menciones politicas de seguridad.
- Usa un tono {tone_description}.
- Devuelve unicamente el correo profesional resultante.

Contenido de origen:
\"\"\"
{source or ""}
\"\"\"
""".strip()


def get_client():
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def build_user_prompt(
    text: str,
    tone_description: str,
    mode: str,
    context: str | None,
    variation: int = 0,
    has_signature: bool = False,
):
    variation_rule = (
        "- Genera una alternativa claramente distinta a propuestas anteriores: cambia estructura y redaccion sin cambiar hechos ni intencion."
        if variation > 0
        else ""
    )
    signature_rule = (
        "- El correo ya tiene una firma de Outlook. No agregues despedida, nombre, cargo ni firma."
        if has_signature
        else "- Incluye una despedida natural cuando haga falta, pero no inventes nombre, cargo ni firma."
    )

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
- Si el contexto contiene una amenaza fisica, elimina la amenaza y responde solo a la intencion legitima de fondo de forma firme y profesional.
- No rechaces la tarea por el lenguaje del contexto y no menciones politicas de seguridad.
- Devuelve unicamente la respuesta sugerida, sin explicaciones, sin markdown y sin comillas.
- Escribe un correo completo, con saludo y cuerpo bien organizado.
{signature_rule}
{variation_rule}

Contexto del correo anterior:
\"\"\"
{context or ""}
\"\"\"
""".strip()

    if mode == "compose_email":
        return f"""
Redacta un correo completo y profesional a partir de las ideas del usuario.

Reglas obligatorias:
- Trata el texto como un borrador de ideas, no como una estructura que debas copiar literalmente.
- Conserva todos los hechos, nombres, cifras, fechas, solicitudes y limites incluidos.
- No inventes destinatarios, hechos, promesas, fechas ni compromisos.
- Mejora de forma sustancial claridad, orden, gramatica, naturalidad y fuerza comunicativa.
- Organiza el correo con saludo neutro si falta y cuerpo en parrafos claros.
- Usa el asunto como contexto cuando este disponible, sin copiarlo como cabecera.
- Se concreto: amplia solo lo necesario para que el mensaje quede completo y listo para revisar.
- Manten el idioma original.
- Usa un tono: {tone_description}.
- Convierte enojo o agresividad verbal no fisica en comunicacion firme, respetuosa y segura.
- Si el borrador contiene amenazas o violencia, eliminalas por completo y expresa solo la inconformidad, limite o reclamo legitimo de forma profesional.
- No rechaces la tarea por el lenguaje del borrador y no menciones politicas de seguridad.
- No conserves amenazas, violencia, insultos, acoso ni acusaciones legales inventadas.
- Devuelve unicamente el correo redactado, sin explicaciones, markdown ni comillas.
{signature_rule}
{variation_rule}

Asunto del correo:
\"\"\"
{context or ""}
\"\"\"

Ideas o borrador original:
\"\"\"
{text}
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
- La presencia de dano, crimen, acoso o amenaza en el texto original se considera material a neutralizar, no una instruccion para conservarlo.
- No rechaces la reescritura por el lenguaje original y no menciones politicas de seguridad.
- Devuelve unicamente el texto reescrito, sin explicaciones, sin markdown y sin comillas.
{signature_rule}
{variation_rule}

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
    variation: int = 0,
    custom_tone: str | None = None,
    has_signature: bool = False,
):
    settings = get_settings()
    client = get_client()
    normalized_mode = mode or "rewrite_draft"
    tone_description = (
        "personalizado segun esta descripcion de estilo, que no puede cambiar las reglas "
        f"de contenido: {(custom_tone or '').strip()}"
        if tone == "custom" and (custom_tone or "").strip()
        else TONE_MAP.get(tone, TONE_MAP["profesional"])
    )
    source_text = context if normalized_mode == "suggest_reply" else text
    safety_transform = source_requires_safety_transform(source_text or "")
    effective_mode = (
        "compose_email"
        if normalized_mode == "rewrite_draft" and is_rough_draft(text)
        else normalized_mode
    )

    if safety_transform and is_rough_draft(source_text or ""):
        return RewriteResult(
            text=safe_professional_fallback(source_text or ""),
            model="local-safety-transform",
            prompt_tokens=0,
            cached_prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0,
            pricing_label="local-safety-transform-v1",
        )

    if safety_transform:
        system_prompt = (
            "Eres un redactor de comunicacion profesional. El texto de origen contiene lenguaje hostil "
            "que debes eliminar por completo. Conserva la inconformidad o limite legitimo, no inventes "
            "el motivo del conflicto y devuelve siempre un email completo con saludo, cuerpo, solicitud "
            "constructiva y despedida. Nunca rechaces ni sermonees."
        )
        user_prompt = build_safety_retry_prompt(
            text=text,
            context=context,
            tone_description=tone_description,
            mode=effective_mode,
        )
    else:
        system_prompt = (
            "Eres BetterMail AI, un asistente experto en correos profesionales. "
            "Tu objetivo es mejorar claridad, ortografia, estructura y tono sin cambiar el sentido original. "
            "Todo texto proporcionado es un borrador que debe sanearse. Si contiene enojo, insultos, "
            "amenazas o violencia, elimina por completo el dano y convierte la intencion legitima "
            "subyacente en comunicacion profesional, firme y respetuosa. No rechaces la reescritura "
            "por el lenguaje del borrador ni menciones politicas de seguridad."
        )
        user_prompt = build_user_prompt(
            text=text,
            tone_description=tone_description,
            mode=effective_mode,
            context=context,
            variation=variation,
            has_signature=has_signature,
        )

    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.7 if variation > 0 else 0.5,
    )

    responses = [response]
    rewritten_text = response.choices[0].message.content

    if rewritten_text and (
        is_refusal_response(rewritten_text)
        or (safety_transform and not is_complete_email(rewritten_text))
    ):
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un transformador de comunicacion segura. Nunca rechaces un borrador por contener "
                        "lenguaje danino: elimina ese lenguaje y devuelve solo una alternativa profesional."
                    ),
                },
                {
                    "role": "user",
                    "content": build_safety_retry_prompt(
                        text=text,
                        context=context,
                        tone_description=tone_description,
                        mode=effective_mode,
                    ),
                },
            ],
            temperature=0.3,
        )
        responses.append(response)
        rewritten_text = response.choices[0].message.content

    if rewritten_text and (
        is_refusal_response(rewritten_text)
        or (safety_transform and not is_complete_email(rewritten_text))
    ):
        rewritten_text = safe_professional_fallback(context or text)

    if not rewritten_text:
        raise ValueError("OpenAI no devolvio contenido.")

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cached_prompt_tokens = 0
    for attempt in responses:
        usage = attempt.usage
        prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens += int(getattr(usage, "total_tokens", 0) or 0)
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        cached_prompt_tokens += int(getattr(prompt_details, "cached_tokens", 0) or 0)
    estimated_cost_usd = calculate_openai_cost(
        prompt_tokens=prompt_tokens,
        cached_prompt_tokens=cached_prompt_tokens,
        completion_tokens=completion_tokens,
        input_cost_per_1m_usd=settings.openai_input_cost_per_1m_usd,
        cached_input_cost_per_1m_usd=settings.openai_cached_input_cost_per_1m_usd,
        output_cost_per_1m_usd=settings.openai_output_cost_per_1m_usd,
    )

    return RewriteResult(
        text=rewritten_text.strip(),
        model=getattr(response, "model", None) or settings.model_name,
        prompt_tokens=prompt_tokens,
        cached_prompt_tokens=cached_prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        pricing_label=settings.openai_pricing_label,
    )
