"""
state.py — Estado de la app Reflex 0.9.x
Usa pydantic.BaseModel en lugar de rx.Base (eliminado en 0.9.4)
Se comunica con FastAPI en localhost:8001 via httpx.
"""
import httpx
import reflex as rx
from pydantic import BaseModel
from datetime import datetime
from typing import List

BACKEND = "http://localhost:8001"


class Fuente(BaseModel):
    archivo: str
    pagina:  int


class Mensaje(BaseModel):
    role:        str
    content:     str
    fuentes:     List[Fuente] = []
    timestamp:   str          = ""
    advertencia: str          = ""
    es_etica:    bool         = True


class AppState(rx.State):
    mensajes:     List[Mensaje] = []
    input_texto:  str           = ""
    input_key:    int           = 0
    cargando:     bool          = False
    indexando:    bool          = False
    bd_lista:     bool          = False
    estado_texto: str           = "Iniciando..."
    error_texto:  str           = ""

    # ── Inicialización ────────────────────────────────────────────────────────
    @rx.event
    async def iniciar(self):
        self.indexando    = True
        self.estado_texto = "Conectando con el servidor..."
        yield
        try:
            async with httpx.AsyncClient(timeout=120.0) as c:
                await c.get(f"{BACKEND}/")
                self.estado_texto = "Indexando documentos PDF..."
                yield
                r    = await c.post(f"{BACKEND}/indexar")
                data = r.json()
            total = data.get("total_chunks", 0)
            proc  = data.get("archivos_procesados", 0)
            if total > 0:
                self.bd_lista     = True
                self.estado_texto = f"✓ {proc} archivo(s) · {total} fragmentos"
            else:
                self.bd_lista     = False
                self.estado_texto = "Coloca PDFs en /documentos y recarga"
        except httpx.ConnectError:
            self.bd_lista     = False
            self.estado_texto = "Backend no disponible"
            self.error_texto  = "Ejecuta: uvicorn backend:api --port 8001"
        except Exception as e:
            self.bd_lista     = False
            self.estado_texto = f"Error: {e}"
        self.indexando = False
        yield

    # ── Enviar mensaje ────────────────────────────────────────────────────────
    @rx.event
    async def enviar(self):
        pregunta = self.input_texto.strip()
        if not pregunta or self.cargando:
            return
        if len(pregunta) < 3:
            self.error_texto = "Escribe una pregunta antes de enviar."
            yield
            return

        self.input_texto = ""
        self.cargando    = True
        self.error_texto = ""
        ts = datetime.now().strftime("%H:%M")

        self.mensajes.append(Mensaje(role="user", content=pregunta, timestamp=ts))
        yield

        if not self.bd_lista:
            self.mensajes.append(Mensaje(
                role="assistant",
                content="⚠️ Base de conocimiento no disponible. Verifica los documentos y el servidor.",
                timestamp=ts,
            ))
            self.cargando = False
            yield
            return

        try:
            async with httpx.AsyncClient(timeout=120.0) as c:
                r = await c.post(
                    f"{BACKEND}/consultar", json={"pregunta": pregunta}
                )
            if r.status_code == 400:
                self.error_texto = r.json().get("detail", "Consulta inválida.")
                self.cargando    = False
                yield
                return
            d = r.json()
            fuentes = [
                Fuente(archivo=f["archivo"], pagina=f["pagina"])
                for f in d.get("fuentes", [])
            ]
            self.mensajes.append(Mensaje(
                role="assistant",
                content=d.get("respuesta", ""),
                fuentes=fuentes,
                timestamp=datetime.now().strftime("%H:%M"),
                advertencia=d.get("advertencia", ""),
                es_etica=d.get("es_etica", True),
            ))
        except httpx.ConnectError:
            self.mensajes.append(Mensaje(
                role="assistant",
                content="No fue posible conectar con el servidor. Verifica que el backend esté activo.",
                timestamp=ts,
            ))
        except Exception as e:
            self.mensajes.append(Mensaje(
                role="assistant",
                content=f"Ocurrió un error al consultar la base de datos: {e}",
                timestamp=ts,
            ))
        self.cargando = False
        yield

    # ── Helpers ───────────────────────────────────────────────────────────────
    @rx.event
    def set_input(self, v: str):
        self.input_texto = v
        self.error_texto = ""

    @rx.event
    def limpiar(self):
        self.mensajes    = []
        self.error_texto = ""

    @rx.event
    async def tecla(self, key: str):
        if key == "Enter":
            yield AppState.enviar()

    @rx.event
    async def recargar(self):
        self.indexando    = True
        self.estado_texto = "Reindexando documentos..."
        self.error_texto  = ""
        yield
        try:
            async with httpx.AsyncClient(timeout=180.0) as c:
                r    = await c.post(f"{BACKEND}/indexar?force=true")
                data = r.json()
            total = data.get("total_chunks", 0)
            proc  = data.get("archivos_procesados", 0)
            self.bd_lista     = total > 0
            self.estado_texto = (
                f"✓ {proc} archivo(s) · {total} fragmentos"
                if total > 0 else "Sin documentos encontrados"
            )
        except Exception as e:
            self.error_texto  = str(e)
            self.estado_texto = "Error al recargar"
        self.indexando = False
        yield

    @rx.event
    def cerrar_error(self):
        self.error_texto = ""