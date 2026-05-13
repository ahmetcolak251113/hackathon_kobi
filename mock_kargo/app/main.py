from fastapi import FastAPI

from app.config import settings
from app.routers.shipments import router as shipments_router

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-cargo-api"}


app.include_router(shipments_router, prefix="/shipments", tags=["shipments"])
