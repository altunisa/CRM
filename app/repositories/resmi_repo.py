from datetime import datetime

from sqlalchemy.orm import Session

from app.models.resmi import ResmiFirma, ResmiFirmaAdresi
from app.schemas.ministry import MinistryFirmPayload


class ResmiFirmaRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_firma(self, payload: MinistryFirmPayload) -> ResmiFirma:
        firma = self.db.get(ResmiFirma, payload.gln)
        now = datetime.utcnow()

        if not firma:
            firma = ResmiFirma(gln=payload.gln)
            self.db.add(firma)

        firma.company_name = payload.company_name
        firma.company_title = payload.company_title
        firma.company_type = payload.company_type
        firma.tax_no = payload.tax_no
        firma.is_active = payload.is_active
        firma.source_system = payload.source_system
        firma.source_last_sync_at = payload.source_last_sync_at or now
        firma.raw_json = payload.raw_json

        self.db.flush()
        self.db.query(ResmiFirmaAdresi).filter(ResmiFirmaAdresi.gln == payload.gln).delete()

        for address in payload.addresses:
            self.db.add(
                ResmiFirmaAdresi(
                    gln=payload.gln,
                    address_type=address.address_type,
                    il=address.il,
                    ilce=address.ilce,
                    mahalle=address.mahalle,
                    posta_kodu=address.posta_kodu,
                    adres=address.adres,
                    latitude=address.latitude,
                    longitude=address.longitude,
                    maps_place_id=address.maps_place_id,
                    raw_json=address.raw_json,
                    source_last_sync_at=payload.source_last_sync_at or now,
                )
            )

        self.db.flush()
        return firma
