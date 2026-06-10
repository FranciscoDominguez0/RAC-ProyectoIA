# CiberAsistente IA — Consultor de Ciberseguridad
**RAG · DeepSeek · sentence-transformers · ChromaDB · FastAPI · Reflex**

---

## 📁 Estructura de archivos

```
mi_asistente/
├── .env                        ← GEMINI_API_KEY=...
├── requirements.txt
├── rxconfig.py
├── backend.py                  ← FastAPI + Uvicorn (puerto 8001)
├── documentos/                 ← ⭐ Coloca aquí tus 5 PDFs
└── app/
    ├── app.py                  ← Entry point Reflex
    ├── state.py                ← Estado + llamadas al backend
    ├── ui.py                   ← Interfaz chat oscura
    └── core/
        ├── indexer.py          ← PDF → chunks → embeddings → ChromaDB
        └── rag_engine.py       ← Filtro ético + RAG + Gemini
```

---

## ⚙️ Instalación

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

Edita `.env`:
```
DEEPSEEK_API_KEY=tu_clave_aqui
```

---

## 📄 Agrega tus 5 PDFs

```
documentos/
├── libro_01_fundamentos_ciberseguridad.pdf
├── libro_02_ataques_y_amenazas.pdf
├── libro_03_redes_y_protocolos.pdf
├── libro_04_criptografia.pdf
└── libro_05_normativas_iso27001.pdf
```

---

## 🚀 Ejecutar (dos terminales)

**Terminal 1 — Backend:**
```bash
uvicorn backend:api --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 — Frontend:**
```bash
reflex run
```

Abre: **http://localhost:3000**

---

## 🔁 Flujo del sistema

**Indexación** (automática al iniciar):
```
PDFs → pypdf (texto por página) → LangChain (fragmentos 800 chars)
     → sentence-transformers → ChromaDB
```

**Consulta:**
```
Pregunta → Filtro ético → ChromaDB (5 fragmentos más similares)
         → DeepSeek → Respuesta + Fuentes (archivo + página)
```

---

## 🛡️ Filtro ético

Bloquea automáticamente preguntas sobre:
- Hackear WiFi ajeno / acceso no autorizado
- Creación de malware o ransomware
- Ataques DDoS / phishing / robo de datos
- Espionaje o doxing

Responde con un mensaje educativo explicando por qué la consulta no es ética.

---

## 📡 API Endpoints

| Método | Ruta        | Descripción                                  |
|--------|-------------|----------------------------------------------|
| GET    | `/`         | Estado del servidor                          |
| GET    | `/stats`    | Estadísticas del índice                      |
| POST   | `/indexar`  | Indexar PDFs (`?force=true` para reindexar)  |
| POST   | `/consultar`| Enviar pregunta → respuesta + fuentes        |

Docs interactivos: **http://localhost:8001/docs**

---

## ⚠️ Advertencia

Esta herramienta proporciona orientación general basada en los documentos cargados.
No sustituye la asesoría de un profesional de ciberseguridad certificado.
