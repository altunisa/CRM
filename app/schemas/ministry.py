from datetime import datetime
from pydantic import BaseModel, Field


class MinistryAddressPayload(BaseModel):
    address_type: str | None = None
    il: str | None = None
    ilce: str | None = None
    mahalle: str | None = None
    posta_kodu: str | None = None
    adres: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    maps_place_id: str | None = None
    raw_json: dict | None = None


class MinistryFirmPayload(BaseModel):
    gln: str = Field(..., min_length=1, max_length=32)
    company_name: str
    company_title: str | None = None
    company_type: str | None = None
    tax_no: str | None = None
    is_active: bool = True
    source_system: str = "BKST"
    source_last_sync_at: datetime | None = None
    raw_json: dict | None = None
    addresses: list[MinistryAddressPayload] = []
