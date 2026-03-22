from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.resmi import BkuRuhsat, BkuTavsiye

router = APIRouter(prefix="/bku", tags=["bku"])


@router.get("/ruhsatlar/top")
def top_ruhsat_sahipleri(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    q = (
        select(BkuRuhsat.ruhsat_sahibi, func.count(BkuRuhsat.id).label("ruhsat_sayisi"))
        .group_by(BkuRuhsat.ruhsat_sahibi)
        .order_by(desc("ruhsat_sayisi"))
        .limit(limit)
    )
    return [dict(r._mapping) for r in db.execute(q)]


@router.get("/tavsiyeler/top")
def top_tavsiyeler(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    q = (
        select(BkuTavsiye.bitki, BkuTavsiye.urun_adi, func.count(BkuTavsiye.id).label("adet"))
        .group_by(BkuTavsiye.bitki, BkuTavsiye.urun_adi)
        .order_by(desc("adet"))
        .limit(limit)
    )
    return [dict(r._mapping) for r in db.execute(q)]
