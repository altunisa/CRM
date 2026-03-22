from sqlalchemy.orm import Session

from app.repositories.crm_repo import CrmRepository
from app.schemas.crm import CrmEnrichmentUpsert


class EnrichmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CrmRepository(db)

    def save_manual_enrichment(self, payload: CrmEnrichmentUpsert):
        row = self.repo.upsert_enrichment(payload)
        self.db.commit()
        return row
