from __future__ import annotations

from fastapi import FastAPI

from app.core.database import Base, engine
from app.routers import bku, crm, crm_firmalar

app = FastAPI(title="BKU Smart CRM", version="2.0.0")

app.include_router(crm.router)
app.include_router(crm_firmalar.router)
app.include_router(bku.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
