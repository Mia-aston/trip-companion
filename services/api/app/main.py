from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.routes.trips import router as trips_router

app = FastAPI(title="Trip Companion API", version="0.1.0")
install_error_handlers(app)
app.include_router(trips_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
