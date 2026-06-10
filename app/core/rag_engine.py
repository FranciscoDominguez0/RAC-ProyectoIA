"""
rag_engine.py — Motor RAG con filtro ético doble + DeepSeek

Filtro capa 1: regex sobre términos ofensivos conocidos
Filtro capa 2: system prompt instruye al LLM a detectar intención ofensiva
               y responder con token BLOQUEADO_ETICO si la detecta
"""
import os
import re
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from app.core import indexer as _indexer

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


# ── Capa 1: filtro por regex ───────────────────────────────────────────────────
PATRON_ETICO = re.compile(
    r'\b('
    # hackear / "como hacker X"
    r'hack(ear|ea|eo|er)\b|c[o0]mo hacker\b|'
    # acceso no autorizado
    r'acceso no autorizado|entrar sin permiso|saltarse (el |la )?(login|autenticaci[oó]n|firewall)|'
    r'bypass de seguridad|evadir (el |la )?(firewall|autenticaci[oó]n)|'
    # robo de datos / credenciales
    r'robar (datos|credenciales|informaci[oó]n|contrase[ñn]as?|claves?|base de datos|registros?)|'
    r'exfiltrar datos|extraer datos sin permiso|obtener datos ajenos|'
    r'contrase[ñn]a ajena|clave ajena|'
    # ataques a bases de datos
    r'(dump(ear)?|volcar) (la |una )?base de datos|sql injection para robar|inyecci[oó]n sql maliciosa|'
    # crear malware / código dañino
    r'(crear|hacer|programar|escribir) (un |una )?(malware|ransomware|troyano|keylogger|spyware|virus)|'
    r'instalar backdoor|infectar (un |el )?(sistema|equipo|servidor)|'
    # ataques de red
    r'(hacer|lanzar|ejecutar|realizar) (un |una )?ataque ddos|como (hacer|lanzar) (un )?ddos|'
    r'atacar (un |el )?servidor|tirar (un |el )?servidor|derribar (un |el )?sitio|'
    r'sniffear contrase[ñn]as?|interceptar tr[aá]fico ajeno|'
    # phishing ofensivo
    r'(hacer|crear|montar) (un )?(phishing|sitio falso) para robar|'
    # espionaje / privacidad
    r'espiar a|doxing|stalkear|rastrear sin permiso|leer correos ajenos|interceptar mensajes ajenos'
    r')',
    re.IGNORECASE | re.UNICODE,
)

def _pasa_filtro_regex(pregunta: str) -> bool:
    return not bool(PATRON_ETICO.search(pregunta))


RESPUESTA_ETICA = (
    "⚠️ **Consulta no permitida**\n\n"
    "Esta pregunta involucra actividades ilegales o no autorizadas. "
    "Como asistente de ciberseguridad mi enfoque es **educativo y defensivo**.\n\n"
    "Puedo ayudarte con:\n"
    "- Cómo proteger tu red WiFi\n"
    "- Buenas prácticas de contraseñas\n"
    "- Detección de intrusiones\n"
    "- Conceptos de seguridad defensiva\n\n"
    "El acceso no autorizado a redes o sistemas es un delito en la mayoría de países."
)

RESPUESTA_NO_INFO = (
    "No encontré información suficiente en los documentos disponibles "
    "para responder esta pregunta."
)

# ── Capa 2: system prompt con detección de intención ofensiva ──────────────────
SYSTEM_PROMPT = """Eres un Asistente Virtual de Ciberseguridad con enfoque EXCLUSIVAMENTE educativo y defensivo.

=== PASO 1 — EVALÚA LA INTENCIÓN (obligatorio antes de responder) ===
Determina si la pregunta busca realizar alguna de estas acciones:
- Acceder sin autorización a redes, sistemas, cuentas o dispositivos ajenos
- Robar, extraer o exfiltrar datos, contraseñas o información de terceros
- Crear o desplegar malware, ransomware, troyanos, keyloggers o código dañino
- Lanzar ataques (DDoS, SQL injection ofensivo, phishing para engañar, MITM para robar, etc.)
- Espiar, rastrear o interceptar comunicaciones de terceros sin consentimiento
- Cualquier acción ilegal aunque esté formulada como "¿cómo funciona?" o "es para aprender"

Si la intención es ofensiva → responde ÚNICAMENTE con el token: BLOQUEADO_ETICO
No agregues explicación, no uses markdown, solo el token exacto.

=== PASO 2 — RESPONDE CON EL CONTEXTO ===
Solo si la intención es legítima y defensiva:
1. Responde ÚNICAMENTE usando el CONTEXTO proporcionado abajo.
2. Si el contexto tiene información relevante, elabora una respuesta clara y profesional.
3. Si el contexto NO tiene información suficiente, responde exactamente: "No encontré información suficiente en los documentos disponibles para responder esta pregunta."
4. NO inventes datos, estadísticas ni conceptos que no estén en el contexto.
5. Menciona las fuentes al final cuando estén disponibles.

CONTEXTO RECUPERADO:
{context}
"""


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

    # Capa 1: regex rápido
    if not _pasa_filtro_regex(pregunta):
        return {
            "respuesta":   RESPUESTA_ETICA,
            "fuentes":     [],
            "es_etica":    False,
            "advertencia": "Consulta bloqueada por razones éticas.",
        }

    # Búsqueda semántica
    fragments = _indexer.search(pregunta, n=5)
    if not fragments:
        return {
            "respuesta":   RESPUESTA_NO_INFO,
            "fuentes":     [],
            "es_etica":    True,
            "advertencia": ADVERTENCIA,
        }

    # Capa 2: LLM con instrucción de detección ética
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
        respuesta = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        respuesta = f"Error al generar la respuesta con DeepSeek: {str(e)}"

    # Capturar token de bloqueo del LLM
    if respuesta.startswith("BLOQUEADO_ETICO"):
        return {
            "respuesta":   RESPUESTA_ETICA,
            "fuentes":     [],
            "es_etica":    False,
            "advertencia": "Consulta bloqueada por razones éticas.",
        }

    # Deduplicar fuentes
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