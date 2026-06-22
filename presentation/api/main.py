from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from presentation.api.routes import payments, subscription, page

def create_app() -> FastAPI:
    app = FastAPI(
        title="VPN Bot API",
        version="1.0.0"
    )

    app.include_router(payments.router)
    app.include_router(subscription.router)
    app.include_router(page.router)

    app.mount("/img", StaticFiles(directory="presentation/api/templates/img"), name="img")

    return app

app = create_app()