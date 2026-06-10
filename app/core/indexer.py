"""
indexer.py — Pipeline completo: PDF → chunks → embeddings → ChromaDB
Consolida: pdf_reader, chunker, embeddings, vector_store, indexer
"""
import os
from pathlib import Path
from typing import List, Dict, Any

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

# ── Configuración ─────────────────────────────────────────────────────────────
DOCS_FOLDER     = "./documentos"
CHROMA_PATH     = "./chroma_db"
COLLECTION_NAME = "ciberseguridad"
MODEL_NAME      = "all-MiniLM-L6-v2"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 100

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[EMBED] Cargando {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    c = chromadb.PersistentClient(path=CHROMA_PATH)
    return c.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


# ── PDF → páginas ─────────────────────────────────────────────────────────────
def _extract_pages(filepath: str) -> List[Dict]:
    path   = Path(filepath)
    reader = PdfReader(str(path))
    pages  = []
    for num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({"text": text, "page": num, "archivo": path.name})
    print(f"[PDF] {path.name}: {len(pages)}/{len(reader.pages)} páginas")
    return pages


# ── Páginas → chunks ──────────────────────────────────────────────────────────
def _split_pages(pages: List[Dict]) -> List[Dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for p in pages:
        for i, text in enumerate(splitter.split_text(p["text"])):
            chunks.append({
                "text":         text,
                "archivo":      p["archivo"],
                "pagina":       p["page"],
                "fragmento_id": f"{p['archivo']}_p{p['page']}_f{i}",
            })
    print(f"[CHUNK] {len(chunks)} fragmentos generados")
    return chunks


# ── API pública ───────────────────────────────────────────────────────────────
def count() -> int:
    try:
        return _get_collection().count()
    except Exception:
        return 0


def clear():
    try:
        chromadb.PersistentClient(path=CHROMA_PATH).delete_collection(COLLECTION_NAME)
    except Exception:
        pass


def search(query: str, n: int = 5) -> List[Dict]:
    col   = _get_collection()
    total = col.count()
    if total == 0:
        return []
    vec = _get_model().encode([query], show_progress_bar=False)[0].tolist()
    res = col.query(
        query_embeddings=[vec], n_results=min(n, total),
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    if res["documents"] and res["documents"][0]:
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            docs.append({"content": doc, "metadata": meta,
                          "similitud": round(1 - dist, 4)})
    return docs


def index_documents(force_reload: bool = False) -> Dict[str, Any]:
    print(f"[INDEX] Iniciando (force={force_reload})")

    if count() > 0 and not force_reload:
        total = count()
        print(f"[INDEX] Ya existen {total} fragmentos. Saltando.")
        return {"total_chunks": total, "archivos_procesados": 0}

    if force_reload:
        clear()

    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)
        return {"total_chunks": 0, "archivos_procesados": 0}

    pdfs = [f for f in Path(DOCS_FOLDER).iterdir()
            if f.is_file() and f.suffix.lower() == ".pdf"]
    if not pdfs:
        return {"total_chunks": 0, "archivos_procesados": 0}

    print(f"[INDEX] Archivos: {[f.name for f in pdfs]}")
    all_chunks, procesados = [], 0

    for pdf in pdfs:
        try:
            chunks = _split_pages(_extract_pages(str(pdf)))
            all_chunks.extend(chunks)
            procesados += 1
        except Exception as e:
            print(f"[INDEX] ERROR {pdf.name}: {e}")

    if all_chunks:
        col      = _get_collection()
        texts    = [c["text"] for c in all_chunks]
        ids      = [c["fragmento_id"] for c in all_chunks]
        metas    = [{"archivo": c["archivo"], "pagina": c["pagina"],
                     "fragmento_id": c["fragmento_id"]} for c in all_chunks]
        model    = _get_model()
        embeds   = model.encode(texts, show_progress_bar=True, batch_size=32).tolist()

        for i in range(0, len(all_chunks), 100):
            e = min(i + 100, len(all_chunks))
            col.add(documents=texts[i:e], embeddings=embeds[i:e],
                    metadatas=metas[i:e], ids=ids[i:e])
        print(f"[INDEX] {len(all_chunks)} fragmentos guardados")

    return {"total_chunks": len(all_chunks), "archivos_procesados": procesados}


def get_stats() -> Dict[str, Any]:
    return {"total_chunks": count(), "collection": COLLECTION_NAME}
