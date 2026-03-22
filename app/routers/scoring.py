from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.scoring_service import ScoringService

router = APIRouter()


@router.post("/recalculate")
def recalculate_scores(db: Session = Depends(get_db)):
    service = ScoringService(db)
    return service.recalculate()