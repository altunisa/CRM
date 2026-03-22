from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.crm import CrmFirmaZenginlestirme
from app.models.resmi import BkuRuhsat, BkuTavsiye, ResmiFirma, ResmiFirmaAdresi
from app.services.classification import normalize_company_name


def tavsiye_heatmap(db: Session, bitki: str | None = None, limit: int = 50):
    query = select(
        BkuTavsiye.bitki,
        BkuTavsiye.aktif_madde,
        func.count(BkuTavsiye.id).label("adet"),
    ).group_by(BkuTavsiye.bitki, BkuTavsiye.aktif_madde)
    if bitki:
        query = query.where(BkuTavsiye.bitki.ilike(f"%{bitki}%"))
    query = query.order_by(desc("adet")).limit(limit)
    return [dict(r._mapping) for r in db.execute(query)]


def opportunities(db: Session, bitki: str | None = None, il: str | None = None, limit: int = 100):
    query = select(
        BkuTavsiye.bitki,
        BkuTavsiye.etmen,
        BkuTavsiye.urun_adi,
        BkuTavsiye.il,
        BkuTavsiye.ilce,
        func.count(BkuTavsiye.id).label("tavsiye_adedi"),
    ).group_by(BkuTavsiye.bitki, BkuTavsiye.etmen, BkuTavsiye.urun_adi, BkuTavsiye.il, BkuTavsiye.ilce)
    if bitki:
        query = query.where(BkuTavsiye.bitki.ilike(f"%{bitki}%"))
    if il:
        query = query.where(BkuTavsiye.il.ilike(f"%{il}%"))
    query = query.order_by(desc("tavsiye_adedi")).limit(limit)
    return [dict(r._mapping) for r in db.execute(query)]


def product_match(db: Session, urun: str | None = None, bitki: str | None = None, il: str | None = None, limit: int = 100):
    q = select(BkuTavsiye.urun_adi, BkuTavsiye.bitki, BkuTavsiye.il, BkuTavsiye.ilce, BkuTavsiye.aktif_madde)
    if urun:
        q = q.where(BkuTavsiye.urun_adi.ilike(f"%{urun}%"))
    if bitki:
        q = q.where(BkuTavsiye.bitki.ilike(f"%{bitki}%"))
    if il:
        q = q.where(BkuTavsiye.il.ilike(f"%{il}%"))

    rows = db.execute(q.limit(limit)).all()
    firms = db.scalars(select(ResmiFirma).limit(500)).all()
    enriched = db.scalars(select(CrmFirmaZenginlestirme)).all()
    enrich_by_gln = {e.gln: e for e in enriched}

    matches = []
    for row in rows:
        norm = normalize_company_name(row.urun_adi)
        for firm in firms:
            if norm and normalize_company_name(firm.company_name)[:6] in norm:
                en = enrich_by_gln.get(firm.gln)
                matches.append(
                    {
                        "gln": firm.gln,
                        "firma": firm.company_name,
                        "urun": row.urun_adi,
                        "bitki": row.bitki,
                        "il": row.il,
                        "ilce": row.ilce,
                        "onerilen_iliski": (en.hedef_iliski_tipi if en else "takip"),
                    }
                )
                break
    return matches[:limit]


def firm_recommendations(db: Session, gln: str, limit: int = 20):
    firm = db.get(ResmiFirma, gln)
    if not firm:
        return []
    address = db.scalar(select(ResmiFirmaAdresi).where(ResmiFirmaAdresi.gln == gln).limit(1))
    il = address.il if address else None

    ruhsat_urunleri = db.scalars(
        select(BkuRuhsat.urun_adi).where(BkuRuhsat.ruhsat_sahibi.ilike(f"%{firm.company_name.split()[0]}%"))
    ).all()

    q = select(BkuTavsiye.bitki, BkuTavsiye.urun_adi, BkuTavsiye.etmen, func.count(BkuTavsiye.id).label("adet")).group_by(
        BkuTavsiye.bitki, BkuTavsiye.urun_adi, BkuTavsiye.etmen
    )
    if il:
        q = q.where(BkuTavsiye.il == il)
    if ruhsat_urunleri:
        q = q.where(BkuTavsiye.urun_adi.not_in(ruhsat_urunleri))
    q = q.order_by(desc("adet")).limit(limit)
    return [dict(r._mapping) for r in db.execute(q)]
