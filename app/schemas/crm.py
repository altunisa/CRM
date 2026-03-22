from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FirmClassificationPatch(BaseModel):
    ruhsat_sahibi: bool | None = None
    uretici: bool | None = None
    ithalatci: bool | None = None
    bayi: bool | None = None
    toptanci: bool | None = None
    distributor: bool | None = None
    karma_firma: bool | None = None
    firma_tipi_ana: str | None = None
    hedef_iliski_tipi: str | None = None
    firma_segment: str | None = None
    stratejik_skor: float | None = None
    kanal_skor: float | None = None
    operasyon_skor: float | None = None
    siniflandirma_notu: str | None = None


class FirmScores(BaseModel):
    gln: str
    stratejik_skor: float
    kanal_skor: float
    operasyon_skor: float
    updated_at: datetime | None
