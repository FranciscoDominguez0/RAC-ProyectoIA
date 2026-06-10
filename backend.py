"""
backend.py — API REST con FastAPI + Uvicorn
Ejecutar: uvicorn backend:api --host 0.0.0.0 --port 8001 --reload
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

from app.core.indexer    import index_documents, get_stats
from app.core.rag_engine import responder_consulta

api = FastAPI(title="CiberAsistente IA", version="1.0.0")

api.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)

# ── Modelos ───────────────────────────────────────────────────────────────────
class ConsultaRequest(BaseModel):
    pregunta: str

class FuenteOut(BaseModel):
    archivo: str
    pagina:  int

class ConsultaResponse(BaseModel):
    respuesta:   str
    fuentes:     List[FuenteOut]
    es_etica:    bool
    advertencia: str

class IndexarResponse(BaseModel):
    total_chunks:        int
    archivos_procesados: int
    mensaje:             str

# ── Endpoints ─────────────────────────────────────────────────────────────────
@api.get("/")
def raiz():
    return {"estado": "activo"}

@api.get("/stats")
def estadisticas():
    return get_stats()

@api.post("/indexar", response_model=IndexarResponse)
def indexar(force: bool = False):
    try:
        stats = index_documents(force_reload=force)
        total = stats["total_chunks"]
        return IndexarResponse(
            total_chunks=total,
            archivos_procesados=stats["archivos_procesados"],
            mensaje=(
                f"{stats['archivos_procesados']} archivo(s), {total} fragmentos indexados."
                if total > 0 else
                "No se encontraron PDFs en /documentos."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/consultar", response_model=ConsultaResponse)
def consultar(body: ConsultaRequest):
    pregunta = body.pregunta.strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="Debe escribir una pregunta.")
    try:
        resultado = responder_consulta(pregunta)
        return ConsultaResponse(**resultado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend:api", host="0.0.0.0", port=8001, reload=True)
