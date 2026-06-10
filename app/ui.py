import reflex as rx
from app.state import AppState, Mensaje as ChatMessage

BG   = "#0b0d12"
SURF = "#111318"
INP  = "#161b24"
BOR  = "#1e2330"
ACC  = "#4f7cff"
TXT  = "#c8d0e8"
MUT  = "#44506e"
DIM  = "#252d42"
GRN  = "#3ecf72"
SANS = "'Inter', sans-serif"
MONO = "'JetBrains Mono', monospace"

EXAMPLES = [
    "Que es ciberseguridad?",
    "Que es un ataque de phishing?",
    "Que es ransomware?",
    "Como funciona MFA?",
    "Controles ISO 27001?",
]

# ── Mensajes ──────────────────────────────────────────────────────────────────
def user_msg(msg: ChatMessage):
    return rx.box(
        rx.text(msg.content, color=TXT, size="2", style={"line_height": "1.7", "font_family": SANS}),
        align_self="flex-end", max_width="60%",
        background="#111827", border=f"1px solid {BOR}",
        border_radius="10px 10px 2px 10px", padding="10px 14px",
    )

def assistant_msg(msg: ChatMessage):
    return rx.hstack(
        rx.box(width="1px", background=ACC, align_self="stretch", opacity="0.4", flex_shrink="0"),
        rx.vstack(
            rx.markdown(msg.content, component_map={
                "p": lambda t: rx.text(t, color=TXT, size="2", style={"line_height": "1.75", "font_family": SANS, "margin_bottom": "6px"}),
                "code": lambda t: rx.code(t, style={"font_family": MONO, "font_size": "12px", "background": INP, "color": ACC, "padding": "1px 5px", "border_radius": "3px"}),
            }),
            align_items="flex-start", spacing="0",
        ),
        gap="14px", align_items="flex-start", align_self="flex-start", max_width="88%",
    )

def message_item(msg: ChatMessage):
    return rx.cond(msg.role == "user", user_msg(msg), assistant_msg(msg))

def typing_indicator():
    return rx.cond(
        AppState.cargando,
        rx.hstack(
            rx.box(width="1px", background=ACC, align_self="stretch", opacity="0.4", flex_shrink="0"),
            rx.hstack(rx.spinner(size="1", color=ACC), rx.text("Procesando", size="2", color=MUT, style={"font_family": SANS}), spacing="2", align="center"),
            gap="14px", align_items="center",
        ),
        rx.box()
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────
def status_line():
    return rx.cond(
        AppState.indexando,
        rx.hstack(
            rx.spinner(size="1", color=MUT),
            rx.text(AppState.estado_texto, size="1", color=MUT, style={"font_family": MONO}),
            spacing="2", align="center",
        ),
        rx.cond(
            AppState.bd_lista,
            rx.hstack(
                rx.box(width="5px", height="5px", border_radius="50%", background=GRN, flex_shrink="0"),
                rx.text(AppState.estado_texto, size="1", color=MUT, style={"font_family": MONO}),
                spacing="2", align="center",
            ),
            rx.text(AppState.estado_texto, size="1", color=MUT, style={"font_family": MONO}),
        )
    )

def sidebar():
    return rx.vstack(
        # Título + estado
        rx.vstack(
            rx.hstack(
                rx.box(width="3px", height="18px", background=ACC, border_radius="2px", flex_shrink="0"),
                rx.text("CiberRAG", size="4", weight="bold", color=TXT,
                        style={"font_family": SANS, "letter_spacing": "-0.02em"}),
                spacing="2", align="center",
            ),
            status_line(),
            spacing="1", padding_bottom="16px",
            border_bottom=f"0.5px solid {BOR}",
            align_items="flex-start", width="100%",
        ),

        # Acciones
        rx.vstack(
            rx.text("ACCIONES", size="1", color="#2e3a52",
                    style={"font_family": MONO, "letter_spacing": "0.12em"}),
            rx.button(
                rx.hstack(rx.icon("refresh-cw", size=12), rx.text("Recargar documentos", size="2"), spacing="2"),
                on_click=AppState.recargar, loading=AppState.indexando,
                width="100%", background="transparent", color=MUT,
                border=f"0.5px solid {BOR}", border_radius="6px",
                padding="7px 10px", cursor="pointer", justify_content="flex-start",
                style={"font_family": SANS, "_hover": {"color": TXT, "border_color": ACC}},
            ),
            rx.button(
                rx.hstack(rx.icon("trash-2", size=12), rx.text("Limpiar conversacion", size="2"), spacing="2"),
                on_click=AppState.limpiar,
                width="100%", background="transparent", color=MUT,
                border=f"0.5px solid {BOR}", border_radius="6px",
                padding="7px 10px", cursor="pointer", justify_content="flex-start",
                style={"font_family": SANS, "_hover": {"color": TXT}},
            ),
            spacing="2", align_items="flex-start", width="100%",
        ),

        # Divisor
        rx.box(height="0.5px", background=BOR, width="100%"),

        # Sugerencias
        rx.vstack(
            rx.text("CONSULTAS FRECUENTES", size="1", color="#2e3a52",
                    style={"font_family": MONO, "letter_spacing": "0.12em"}),
            *[rx.button(
                q, on_click=AppState.set_input(q),
                width="100%", background="transparent", color=MUT,
                border="none", border_radius="4px", padding="5px 8px",
                cursor="pointer", justify_content="flex-start",
                style={"font_family": SANS, "font_size": "12px", "white_space": "normal",
                       "text_align": "left", "line_height": "1.5",
                       "_hover": {"color": TXT, "background": INP}},
            ) for q in EXAMPLES],
            spacing="1", align_items="flex-start", width="100%",
        ),

        rx.spacer(),
        rx.text("v1.0 — RAG + DeepSeek", size="1", color=DIM,
                style={"font_family": MONO, "padding_top": "14px",
                       "border_top": f"0.5px solid {BOR}"}),

        spacing="5", align_items="flex-start",
        width="248px", min_width="248px", height="100vh",
        overflow_y="auto", padding="20px 14px",
        background=SURF, border_right=f"0.5px solid {BOR}",
    )

# ── Chat ──────────────────────────────────────────────────────────────────────
def chat_input():
    return rx.box(
        rx.hstack(
            rx.text_area(
                key=AppState.input_key, placeholder="Escribe tu consulta...",
                value=AppState.input_texto, on_change=AppState.set_input,
                on_key_down=AppState.tecla, rows="1", flex="1",
                background=INP, color=TXT,
                border=f"1px solid {BOR}", border_radius="8px",
                padding="10px 13px", font_size="14px", resize="none", outline="none",
                style={"font_family": SANS, "_placeholder": {"color": DIM},
                       "_focus": {"border_color": ACC, "box_shadow": f"0 0 0 2px {ACC}18"}},
            ),
            rx.button(
                rx.icon("arrow-up", size=15),
                on_click=AppState.enviar, loading=AppState.cargando,
                disabled=AppState.input_texto.length() == 0,
                background=ACC, color="white", border="none",
                border_radius="8px", width="40px", height="40px",
                cursor="pointer", flex_shrink="0",
                style={"_hover": {"background": "#3d68e8"},
                       "_disabled": {"background": INP, "color": DIM, "cursor": "not-allowed"}},
            ),
            spacing="2", align="end",
        ),
        padding="12px 24px 18px",
        border_top=f"1px solid {BOR}",
        background=BG, flex_shrink="0",
    )

def chat_area():
    return rx.vstack(
        rx.box(
            rx.cond(
                AppState.mensajes.length() == 0,
                rx.vstack(
                    rx.box(width="28px", height="1px", background=ACC),
                    rx.text("Consultor de Ciberseguridad", size="5", weight="medium", color=TXT,
                            style={"font_family": SANS, "letter_spacing": "-0.02em"}),
                    rx.text("Haz preguntas basadas en los documentos cargados.", size="2", color=MUT,
                            style={"font_family": SANS}),
                    align="center", spacing="3", justify="center", height="100%", min_height="300px",
                ),
                rx.box()
            ),
            rx.vstack(
                rx.foreach(AppState.mensajes, message_item),
                typing_indicator(),
                spacing="4", width="100%", padding_y="28px",
            ),
            id="msgs", flex="1", overflow_y="auto", width="100%", padding_x="28px",
        ),
        chat_input(),
        rx.script("""
            (function(){var e=document.getElementById('msgs');if(!e)return;
            function s(){e.scrollTop=e.scrollHeight;}
            new MutationObserver(s).observe(e,{childList:true,subtree:true});s();})();
        """),
        spacing="0", flex="1", height="100vh",
        overflow="hidden", background=BG, align_items="stretch",
    )

def index():
    return rx.hstack(
        sidebar(), chat_area(),
        spacing="0", height="100vh",
        overflow="hidden", background=BG, align_items="stretch",
    )