from fastapi import FastAPI

from app.config import settings
from app.routers.companies import router as companies_router
from app.routers.products import router as products_router
from app.routers.shipments import router as shipments_router

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-cargo-api"}


app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(companies_router, prefix="/companies", tags=["companies"])
app.include_router(shipments_router, prefix="/shipments", tags=["shipments"])
