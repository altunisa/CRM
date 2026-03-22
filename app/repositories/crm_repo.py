from sqlalchemy.orm import Session

from app.models.crm import CrmFirmaZenginlestirme
from app.schemas.crm import CrmEnrichmentUpsert


class CrmRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_enrichment(self, payload: CrmEnrichmentUpsert) -> CrmFirmaZenginlestirme:
        row = self.db.get(CrmFirmaZenginlestirme, payload.gln)
        if not row:
            row = CrmFirmaZenginlestirme(gln=payload.gln)
            self.db.add(row)

        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(row, field, value)

        self.db.flush()
        return row
