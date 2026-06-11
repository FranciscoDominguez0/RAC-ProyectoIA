"""
rag_engine.py — Motor RAG con clasificacion etica de 3 niveles + DeepSeek

Nivel 1 — Bloqueo total:   intencion claramente maliciosa (regex rapido)
Nivel 2 — Conversion:      pregunta ambigua redirigida a enfoque defensivo (LLM)
Nivel 3 — Respuesta libre: pregunta legitima, se responde con contexto RAG (LLM)
"""
import os
import re
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from app.core import indexer as _indexer

load_dotenv(override=True)

# ── DeepSeek ──────────────────────────────────────────────────────────────────
LLM_MODEL = "deepseek-chat"
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY no configurada en .env")
        _client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    return _client


# ── Nivel 1: regex — bloqueo inmediato sin llamar al LLM ─────────────────────
# Patrones que indican intención claramente ofensiva o ilegal.
_PATRON_NIVEL1 = re.compile(
    r'\b('
    r'hack(ear|ea|eo|er)|'
    r'robar\s+(datos|credenciales|contrase[ñn]as?|claves?)|'
    r'exfiltrar\s+datos|contrase[ñn]a\s+ajena|clave\s+ajena|'
    r'(crear|hacer|programar)\s+(un\s+)?(malware|ransomware|troyano|keylogger|virus)|'
    r'instalar\s+backdoor|infectar\s+(un\s+)?(sistema|servidor)|'
    r'ataque\s+ddos|tirar\s+(un\s+)?servidor|'
    r'sniffear|doxing|stalkear|interceptar\s+(tr[aá]fico|mensajes)\s+ajenos?'
    r')',
    re.IGNORECASE | re.UNICODE,
)

_RESPUESTA_NIVEL1 = (
    "No puedo ayudar con actividades ilegales o ataques a sistemas.\n\n"
    "Puedo explicarte estos conceptos desde una perspectiva defensiva y educativa."
)

# ── Nivel 2 y 3: system prompt para el LLM ───────────────────────────────────
# El LLM clasifica la pregunta y responde según el nivel.
_SYSTEM_PROMPT = """Eres un asistente de ciberseguridad educativo y defensivo. Respuestas concisas, sin emojis.

Si la pregunta tiene enfoque ofensivo (hackear, explotar, atacar): declina brevemente y ofrece 3-4 puntos sobre como defenderse o practicarlo legalmente.

Si la pregunta es legitima: responde usando solo el CONTEXTO. Si no hay informacion suficiente, di: "No encontre informacion suficiente en los documentos disponibles." Si respondiste con el contexto, agrega al final:

Fuentes:
- [archivo], pagina [numero]

CONTEXTO:
{context}
"""

_RESPUESTA_NO_INFO = (
    "No encontre informacion suficiente en los documentos disponibles "
    "para responder esta pregunta."
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _build_context(fragments: List[Dict]) -> str:
    parts = []
    for i, f in enumerate(fragments, 1):
        archivo = f["metadata"].get("archivo", "Desconocido")
        pagina  = f["metadata"].get("pagina", "?")
        parts.append(
            f"[Fragmento {i} — {archivo}, Pagina {pagina}]\n{f['content'].strip()}"
        )
    return "\n\n---\n\n".join(parts)


def _llamar_llm(system: str, pregunta: str) -> str:
    resp = _get_client().chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": pregunta},
        ],
        max_tokens=1024,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _deduplicar_fuentes(fragments: List[Dict]) -> List[Dict]:
    seen, fuentes = set(), []
    for f in fragments:
        key = (f["metadata"].get("archivo", ""), f["metadata"].get("pagina", 0))
        if key not in seen:
            seen.add(key)
            fuentes.append({"archivo": key[0], "pagina": key[1]})
    return fuentes


# ── API publica ───────────────────────────────────────────────────────────────
def responder_consulta(pregunta: str) -> Dict[str, Any]:
    # Nivel 1: bloqueo inmediato por regex
    if _PATRON_NIVEL1.search(pregunta):
        return {
            "respuesta":   _RESPUESTA_NIVEL1,
            "fuentes":     [],
            "es_etica":    False,
            "advertencia": "",
        }

    # Busqueda semantica en la base de conocimiento
    fragments = _indexer.search(pregunta, n=5)
    context   = _build_context(fragments) if fragments else "(sin contexto disponible)"
    prompt    = _SYSTEM_PROMPT.format(context=context)

    try:
        respuesta = _llamar_llm(prompt, pregunta)
    except Exception as e:
        return {
            "respuesta":   f"Error al generar la respuesta: {e}",
            "fuentes":     [],
            "es_etica":    True,
            "advertencia": "",
        }

    # Nivel 2 no devuelve fuentes (no uso real del RAG)
    # Nivel 3 si — el LLM usó el contexto, incluir fuentes
    fuentes = _deduplicar_fuentes(fragments) if fragments else []

    return {
        "respuesta":   respuesta,
        "fuentes":     fuentes,
        "es_etica":    True,
        "advertencia": "",
    }