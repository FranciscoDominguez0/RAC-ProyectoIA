import reflex as rx
from app.ui import index
from app.state import AppState

app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap"
    ],
    style={"background": "#0b0d12"},
)

app.add_page(
    index,
    route="/",
    title="CiberAsistente",
    on_load=AppState.iniciar,
)
