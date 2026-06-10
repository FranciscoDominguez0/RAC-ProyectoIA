"""
rag_engine.py — Motor RAG con filtro ético + DeepSeek

Flujo:
  1. Filtro ético: bloquea preguntas ilegales/dañinas
  2. Búsqueda semántica en ChromaDB (5 fragmentos)
  3. Construcción de contexto con archivo y página
  4. Llamada a DeepSeek con instrucciones estrictas
  5. Retorna respuesta + fuentes (archivo + página)
"""
import os
import re
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from app.core.indexer import search

load_dotenv()

# ── DeepSeek ──────────────────────────────────────────────────────────────────
LLM_MODEL = "deepseek-chat"
_client   = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY no configurada en .env")
        _client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    return _client


# ── Filtro ético ──────────────────────────────────────────────────────────────
PATRON_ETICO = re.compile(
    r"\b(hackear|hackea|hacker el wifi|hackear wifi|robar wifi|crackear|"
    r"acceso no autorizado|contraseña ajena|clave ajena|espiar a|"
    r"infectar|propagar virus|crear malware|ataque ddos|"
    r"ransomware como hacer|phishing para robar|robar datos|robar credenciales|"
    r"bypass de seguridad|evadir firewall|entrar sin permiso|"
    r"atacar servidor|derribar sitio|doxing|stalkear|"
    r"hackear cuenta|hackear celular|hackear computadora|"
    r"sniffear contraseñas|interceptar trafico ajeno)\b",
    re.IGNORECASE | re.UNICODE,
)

RESPUESTA_ETICA = (
    "⚠️ **Consulta no permitida por razones éticas**\n\n"
    "Esta pregunta involucra actividades ilegales, no autorizadas o que podrían "
    "causar daño a terceros. Como asistente de ciberseguridad, mi función es "
    "**educativa y defensiva**: ayudar a entender conceptos, proteger sistemas "
    "y aprender buenas prácticas.\n\n"
    "Puedo ayudarte con:\n"
    "- ¿Cómo proteger tu propia red WiFi?\n"
    "- Buenas prácticas de contraseñas seguras\n"
    "- Cómo detectar intrusiones en tu red\n"
    "- Conceptos de seguridad defensiva y cifrado\n\n"
    "Recuerda: el acceso no autorizado a redes o sistemas es un delito tipificado "
    "en la mayoría de países."
)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un Asistente Virtual Profesional de Ciberseguridad con enfoque educativo y defensivo.

REGLAS OBLIGATORIAS:
1. Responde SOLO usando el CONTEXTO proporcionado abajo.
2. Si el contexto tiene información relacionada, elabora una respuesta clara y profesional.
3. Si el contexto NO tiene información suficiente, responde exactamente: "No encontré información suficiente en los documentos disponibles. Consulta a un especialista o agrega más fuentes al sistema."
4. NO inventes datos, estadísticas ni conceptos que no estén en el contexto.
5. NO respondas preguntas sobre cómo realizar ataques, accesos no autorizados ni actividades ilegales.
6. Eres educativo y defensivo: explica conceptos, protección y buenas prácticas.
7. Menciona las fuentes cuando estén disponibles al final de tu respuesta.

CONTEXTO RECUPERADO:
{context}
"""


def _es_etica(pregunta: str) -> bool:
    return not bool(PATRON_ETICO.search(pregunta))


def _build_context(fragments: List[Dict]) -> str:
    parts = []
    for i, f in enumerate(fragments, 1):
        archivo = f["metadata"].get("archivo", "Desconocido")
        pagina  = f["metadata"].get("pagina", "?")
        parts.append(
            f"[Fragmento {i} — {archivo}, Página {pagina}]\n{f['content'].strip()}"
        )
    return "\n\n---\n\n".join(parts)


def responder_consulta(pregunta: str) -> Dict[str, Any]:
    ADVERTENCIA = (
        "⚠️ Esta información es orientativa y se basa en los documentos cargados. "
        "No sustituye la asesoría de un profesional de ciberseguridad certificado."
    )

    # 1. Filtro ético
    if not _es_etica(pregunta):
        return {
            "respuesta":   RESPUESTA_ETICA,
            "fuentes":     [],
            "es_etica":    False,
            "advertencia": "Consulta bloqueada por razones éticas.",
        }

    # 2. Búsqueda semántica
    fragments = search(pregunta, n=5)
    if not fragments:
        return {
            "respuesta": (
                "No encontré información suficiente en los documentos disponibles. "
                "Verifica que los PDFs estén en /documentos y que la indexación esté completa."
            ),
            "fuentes":     [],
            "es_etica":    True,
            "advertencia": ADVERTENCIA,
        }

    # 3. Llamar a DeepSeek
    context = _build_context(fragments)
    prompt  = SYSTEM_PROMPT.format(context=context)

    try:
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": pregunta},
            ],
            max_tokens=1024,
            temperature=0.2,
        )
        respuesta = resp.choices[0].message.content or ""
    except Exception as e:
        respuesta = f"Error al generar la respuesta con DeepSeek: {str(e)}"

    # 4. Deduplicar fuentes
    seen, fuentes = set(), []
    for f in fragments:
        key = (f["metadata"].get("archivo", ""), f["metadata"].get("pagina", 0))
        if key not in seen:
            seen.add(key)
            fuentes.append({"archivo": key[0], "pagina": key[1]})

    return {
        "respuesta":   respuesta,
        "fuentes":     fuentes,
        "es_etica":    True,
        "advertencia": ADVERTENCIA,
    }
