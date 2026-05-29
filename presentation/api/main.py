from fastapi import FastAPI

from presentation.api.routes import payments

def create_app() -> FastAPI:
    app = FastAPI(
        title="VPN Bot API",
        version="1.0.0"
    )

    app.include_router(payments.router)

    return app

app = create_app()