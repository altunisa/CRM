from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CrmFirmaZenginlestirme(Base):
    __tablename__ = "crm_firma_zenginlestirme"

    gln: Mapped[str] = mapped_column(ForeignKey("resmi_firmalar.gln"), primary_key=True)

    ruhsat_sahibi: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    uretici: Mapped[bool] = mapped_column(Boolean, default=False)
    ithalatci: Mapped[bool] = mapped_column(Boolean, default=False)
    bayi: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    toptanci: Mapped[bool] = mapped_column(Boolean, default=False)
    distributor: Mapped[bool] = mapped_column(Boolean, default=False)
    karma_firma: Mapped[bool] = mapped_column(Boolean, default=False)

    firma_tipi_ana: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hedef_iliski_tipi: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    firma_segment: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    stratejik_skor: Mapped[float] = mapped_column(Float, default=0.0)
    kanal_skor: Mapped[float] = mapped_column(Float, default=0.0)
    operasyon_skor: Mapped[float] = mapped_column(Float, default=0.0)

    siniflandirma_notu: Mapped[str | None] = mapped_column(Text, nullable=True)
    siniflandirma_kaynagi: Mapped[str | None] = mapped_column(String(64), nullable=True)
    siniflandirma_guncelleme_tarihi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CrmFirmaAktivitesi(Base):
    __tablename__ = "crm_firma_aktivitesi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gln: Mapped[str] = mapped_column(ForeignKey("resmi_firmalar.gln"), index=True)
    aktivite_tipi: Mapped[str] = mapped_column(String(64), index=True)
    aciklama: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
