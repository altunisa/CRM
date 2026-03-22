from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resmi import ResmiFirmaAdresi


class AddressRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_gln(self, gln: str) -> list[ResmiFirmaAdresi]:
        stmt = select(ResmiFirmaAdresi).where(ResmiFirmaAdresi.gln == gln)
        return list(self.db.scalars(stmt).all())
