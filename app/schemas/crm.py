from datetime import datetime
from pydantic import BaseModel, EmailStr


class CrmEnrichmentUpsert(BaseModel):
    gln: str
    phone_mobile: str | None = None
    phone_office: str | None = None
    email_marketing: EmailStr | None = None
    authorized_person: str | None = None
    authorized_title: str | None = None
    annual_potential_volume: float | None = None
    current_competitor_brands: str | None = None
    customer_note: str | None = None
    enrichment_status: str | None = None
    enriched_by: str | None = None
    enriched_at: datetime | None = None
