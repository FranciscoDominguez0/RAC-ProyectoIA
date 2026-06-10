import reflex as rx

config = rx.Config(
    app_name="app",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="dark", accent_color="blue")
        )
    ],
)
