from fastapi import FastAPI
from app.core.config import settings
from app.routers import crm, geo, ministry, scoring, bku, crm_firmalar

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.include_router(ministry.router, prefix="/ministry", tags=["Ministry"])
app.include_router(crm.router, prefix="/crm", tags=["CRM"])
app.include_router(crm_firmalar.router, prefix="/crm/firms", tags=["CRM Firms"])
app.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
app.include_router(geo.router, prefix="/geo", tags=["Geo"])
app.include_router(bku.router)

@app.get("/")
def root():
    return {"status": "ok", "app": settings.APP_NAME}