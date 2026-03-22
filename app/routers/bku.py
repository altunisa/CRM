from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.bku import BkuTavsiye
from app.core.database import get_db
from fastapi import Depends, Query
from typing import Optional
router = APIRouter(prefix="/bku", tags=["BKÜ Tavsiyeler"])
router = APIRouter(prefix="/bku", tags=["BKU"])

@router.get("/ruhsatlar")
def bku_ruhsatlari(
    q: str = Query(default=""),
    limit: int = Query(default=100),
    db: Session = Depends(get_db),
):
    sql = text("""
        SELECT id, urun_adi, ruhsat_durumu, aktif_madde, firma, ruhsat_tarihi, ruhsat_no, formulasyon
        FROM bku_ruhsatlar
        WHERE
            (:q = '')
            OR urun_adi ILIKE :like_q
            OR aktif_madde ILIKE :like_q
            OR firma ILIKE :like_q
            OR ruhsat_no ILIKE :like_q
        ORDER BY ruhsat_tarihi DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(
        sql,
        {"q": q, "like_q": f"%{q}%", "limit": limit}
    ).mappings().all()

    return {"items": [dict(r) for r in rows]}
@router.get("/tavsiyeler")
def get_tavsiyeler(
    bitki: Optional[str] = Query(None),
    zararli: Optional[str] = Query(None),
    aktif_madde: Optional[str] = Query(None),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(BkuTavsiye)

    if bitki:
        query = query.filter(BkuTavsiye.bitki_adi.ilike(f"%{bitki}%"))

    if zararli:
        query = query.filter(BkuTavsiye.zararli_organizma.ilike(f"%{zararli}%"))

    if aktif_madde:
        query = query.filter(BkuTavsiye.aktif_madde.ilike(f"%{aktif_madde}%"))

    total = query.count()

    data = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": data
    }