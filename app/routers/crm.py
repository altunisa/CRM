from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.opportunity import firm_recommendations, opportunities, product_match, tavsiye_heatmap

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/opportunities")
def list_opportunities(
    bitki: str | None = None,
    il: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return opportunities(db, bitki=bitki, il=il, limit=limit)


@router.get("/product-match")
def list_product_match(
    urun: str | None = None,
    bitki: str | None = None,
    il: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return product_match(db, urun=urun, bitki=bitki, il=il, limit=limit)


@router.get("/tavsiyeler/heatmap")
def tavsiye_heatmap_view(
    bitki: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return tavsiye_heatmap(db, bitki=bitki, limit=limit)


@router.get("/firms/{gln}/recommendations")
def firm_recommendations_view(
    gln: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return firm_recommendations(db, gln=gln, limit=limit)
