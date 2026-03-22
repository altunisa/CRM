from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crm import CrmFirmaZenginlestirme
from app.models.resmi import ResmiFirma, ResmiFirmaAdresi
from app.schemas.crm import FirmClassificationPatch
from app.services.classification import classify_all_firms, classify_single_firm

router = APIRouter(prefix="/crm/firms", tags=["crm-firmalar"])


@router.get("")
def list_firms(
    q: str | None = None,
    il: str | None = None,
    ilce: str | None = None,
    firma_tipi_ana: str | None = None,
    hedef_iliski_tipi: str | None = None,
    firma_segment: str | None = None,
    ruhsat_sahibi: bool | None = None,
    bayi: bool | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(ResmiFirma, CrmFirmaZenginlestirme, ResmiFirmaAdresi).join(
        CrmFirmaZenginlestirme,
        CrmFirmaZenginlestirme.gln == ResmiFirma.gln,
        isouter=True,
    ).join(
        ResmiFirmaAdresi,
        ResmiFirmaAdresi.gln == ResmiFirma.gln,
        isouter=True,
    )

    if q:
        stmt = stmt.where(ResmiFirma.company_name.ilike(f"%{q}%"))
    if il:
        stmt = stmt.where(ResmiFirmaAdresi.il == il)
    if ilce:
        stmt = stmt.where(ResmiFirmaAdresi.ilce == ilce)
    if firma_tipi_ana:
        stmt = stmt.where(CrmFirmaZenginlestirme.firma_tipi_ana == firma_tipi_ana)
    if hedef_iliski_tipi:
        stmt = stmt.where(CrmFirmaZenginlestirme.hedef_iliski_tipi == hedef_iliski_tipi)
    if firma_segment:
        stmt = stmt.where(CrmFirmaZenginlestirme.firma_segment == firma_segment)
    if ruhsat_sahibi is not None:
        stmt = stmt.where(CrmFirmaZenginlestirme.ruhsat_sahibi == ruhsat_sahibi)
    if bayi is not None:
        stmt = stmt.where(CrmFirmaZenginlestirme.bayi == bayi)

    rows = db.execute(stmt.limit(limit)).all()
    return [
        {
            "gln": r.ResmiFirma.gln,
            "firma": r.ResmiFirma.company_name,
            "il": r.ResmiFirmaAdresi.il if r.ResmiFirmaAdresi else None,
            "ilce": r.ResmiFirmaAdresi.ilce if r.ResmiFirmaAdresi else None,
            "classification": {
                "firma_tipi_ana": r.CrmFirmaZenginlestirme.firma_tipi_ana if r.CrmFirmaZenginlestirme else None,
                "hedef_iliski_tipi": r.CrmFirmaZenginlestirme.hedef_iliski_tipi if r.CrmFirmaZenginlestirme else None,
                "firma_segment": r.CrmFirmaZenginlestirme.firma_segment if r.CrmFirmaZenginlestirme else None,
                "ruhsat_sahibi": r.CrmFirmaZenginlestirme.ruhsat_sahibi if r.CrmFirmaZenginlestirme else None,
            },
        }
        for r in rows
    ]


@router.get("/top/list")
def top_firms(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(ResmiFirma, CrmFirmaZenginlestirme).join(
        CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln, isouter=True
    ).order_by(desc(CrmFirmaZenginlestirme.stratejik_skor))
    rows = db.execute(stmt.limit(limit)).all()
    return [
        {
            "gln": r.ResmiFirma.gln,
            "firma": r.ResmiFirma.company_name,
            "stratejik_skor": r.CrmFirmaZenginlestirme.stratejik_skor if r.CrmFirmaZenginlestirme else 0,
            "kanal_skor": r.CrmFirmaZenginlestirme.kanal_skor if r.CrmFirmaZenginlestirme else 0,
            "operasyon_skor": r.CrmFirmaZenginlestirme.operasyon_skor if r.CrmFirmaZenginlestirme else 0,
        }
        for r in rows
    ]


@router.get("/{gln}")
def firm_detail(gln: str, db: Session = Depends(get_db)):
    firm = db.get(ResmiFirma, gln)
    if not firm:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")
    enrich = db.get(CrmFirmaZenginlestirme, gln)
    addresses = db.scalars(select(ResmiFirmaAdresi).where(ResmiFirmaAdresi.gln == gln)).all()
    return {
        "gln": firm.gln,
        "company_name": firm.company_name,
        "classification": ({
            "ruhsat_sahibi": enrich.ruhsat_sahibi,
            "uretici": enrich.uretici,
            "ithalatci": enrich.ithalatci,
            "bayi": enrich.bayi,
            "toptanci": enrich.toptanci,
            "distributor": enrich.distributor,
            "karma_firma": enrich.karma_firma,
            "firma_tipi_ana": enrich.firma_tipi_ana,
            "hedef_iliski_tipi": enrich.hedef_iliski_tipi,
            "firma_segment": enrich.firma_segment,
            "stratejik_skor": enrich.stratejik_skor,
            "kanal_skor": enrich.kanal_skor,
            "operasyon_skor": enrich.operasyon_skor,
            "siniflandirma_notu": enrich.siniflandirma_notu,
            "siniflandirma_kaynagi": enrich.siniflandirma_kaynagi,
            "siniflandirma_guncelleme_tarihi": enrich.siniflandirma_guncelleme_tarihi,
        } if enrich else None),
        "addresses": [{"il":a.il, "ilce":a.ilce, "adres":a.adres} for a in addresses],
    }


@router.get("/{gln}/scores")
def firm_scores(gln: str, db: Session = Depends(get_db)):
    enrich = db.get(CrmFirmaZenginlestirme, gln)
    if not enrich:
        raise HTTPException(status_code=404, detail="Skor bulunamadı")
    return {
        "gln": gln,
        "stratejik_skor": enrich.stratejik_skor,
        "kanal_skor": enrich.kanal_skor,
        "operasyon_skor": enrich.operasyon_skor,
        "updated_at": enrich.siniflandirma_guncelleme_tarihi,
    }


@router.post("/classify")
def classify_firms(limit: int = Query(default=500, ge=1, le=10000), db: Session = Depends(get_db)):
    count = classify_all_firms(db, limit=limit)
    return {"classified_count": count}


@router.post("/{gln}/classify")
def classify_one(gln: str, db: Session = Depends(get_db)):
    firm = db.get(ResmiFirma, gln)
    if not firm:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")
    enriched = classify_single_firm(db, firm)
    db.commit()
    return {"gln": gln, "classification": {"firma_tipi_ana": enriched.firma_tipi_ana, "hedef_iliski_tipi": enriched.hedef_iliski_tipi, "firma_segment": enriched.firma_segment}}


@router.patch("/{gln}/classification")
def patch_classification(gln: str, payload: FirmClassificationPatch, db: Session = Depends(get_db)):
    enrich = db.get(CrmFirmaZenginlestirme, gln)
    if not enrich:
        enrich = CrmFirmaZenginlestirme(gln=gln)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(enrich, field, value)
    enrich.siniflandirma_kaynagi = "manual_patch"
    enrich.siniflandirma_guncelleme_tarihi = datetime.utcnow()
    db.add(enrich)
    db.commit()
    db.refresh(enrich)
    return {"gln": enrich.gln, "firma_tipi_ana": enrich.firma_tipi_ana, "hedef_iliski_tipi": enrich.hedef_iliski_tipi, "firma_segment": enrich.firma_segment, "updated_at": enrich.siniflandirma_guncelleme_tarihi}
