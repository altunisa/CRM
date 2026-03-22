from fastapi import APIRouter, Depends
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crm import CrmUrunHedefleme
from app.models.resmi import ResmiFirma, ResmiFirmaAdresi

router = APIRouter()


def segment_color(oncelik: str | None) -> str:
    if oncelik == "A":
        return "red"
    if oncelik == "B":
        return "orange"
    if oncelik == "C":
        return "yellow"
    return "gray"


@router.get("/iller")
def get_iller(db: Session = Depends(get_db)):
    rows = (
        db.query(ResmiFirmaAdresi.il)
        .filter(ResmiFirmaAdresi.il.isnot(None))
        .distinct()
        .order_by(ResmiFirmaAdresi.il.asc())
        .all()
    )
    return [r[0] for r in rows if r[0]]


@router.get("/ilceler")
def get_ilceler(il: str, db: Session = Depends(get_db)):
    rows = (
        db.query(ResmiFirmaAdresi.ilce)
        .filter(
            ResmiFirmaAdresi.il == il,
            ResmiFirmaAdresi.ilce.isnot(None)
        )
        .distinct()
        .order_by(ResmiFirmaAdresi.ilce.asc())
        .all()
    )
    return [r[0] for r in rows if r[0]]


@router.get("/map-points")
def get_map_points(
    urun_kodu: str,
    oncelik: str | None = None,
    il: str | None = None,
    ilce: str | None = None,
    firma_tipi: str | None = None,
    adres_tipi: str | None = None,
    min_skor: int | None = None,
    limit: int = 2000,
    db: Session = Depends(get_db),
):
    query = (
        db.query(CrmUrunHedefleme, ResmiFirma, ResmiFirmaAdresi)
        .join(ResmiFirma, ResmiFirma.gln == CrmUrunHedefleme.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == CrmUrunHedefleme.gln)
        .filter(
            CrmUrunHedefleme.urun_kodu == urun_kodu,
            ResmiFirmaAdresi.latitude.isnot(None),
            ResmiFirmaAdresi.longitude.isnot(None),
        )
    )

    if oncelik:
        query = query.filter(CrmUrunHedefleme.oncelik_sinifi == oncelik)
    if il:
        query = query.filter(ResmiFirmaAdresi.il == il)
    if ilce:
        query = query.filter(ResmiFirmaAdresi.ilce == ilce)
    if firma_tipi:
        query = query.filter(ResmiFirma.company_type == firma_tipi)
    if adres_tipi:
        query = query.filter(ResmiFirmaAdresi.address_type == adres_tipi)
    if min_skor is not None:
        query = query.filter(CrmUrunHedefleme.toplam_skor >= min_skor)

    results = query.order_by(CrmUrunHedefleme.toplam_skor.desc()).limit(limit).all()

    return [
        {
            "gln": h.gln,
            "firma_adi": f.company_name,
            "firma_tipi": f.company_type,
            "adres_tipi": a.address_type,
            "urun_kodu": h.urun_kodu,
            "urun_adi": h.urun_adi,
            "il": a.il,
            "ilce": a.ilce,
            "mahalle": a.mahalle,
            "adres": a.adres,
            "latitude": float(a.latitude),
            "longitude": float(a.longitude),
            "skor": h.toplam_skor,
            "oncelik": h.oncelik_sinifi,
            "renk": segment_color(h.oncelik_sinifi),
        }
        for (h, f, a) in results
    ]