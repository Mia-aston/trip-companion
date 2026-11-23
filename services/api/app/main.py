from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.routes.places import router as places_router
from app.api.routes.trips import router as trips_router
from app.config import get_settings

app = FastAPI(title="Trip Companion API", version="0.1.0")
install_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["content-type", "idempotency-key"],
)
app.include_router(trips_router)
app.include_router(places_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
