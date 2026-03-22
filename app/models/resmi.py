from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResmiFirma(Base):
    __tablename__ = "resmi_firmalar"

    gln: Mapped[str] = mapped_column(String(13), primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    vergi_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    addresses: Mapped[list[ResmiFirmaAdresi]] = relationship(back_populates="firma")


class ResmiFirmaAdresi(Base):
    __tablename__ = "resmi_firma_adresleri"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gln: Mapped[str] = mapped_column(ForeignKey("resmi_firmalar.gln"), index=True)
    il: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ilce: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    adres: Mapped[str | None] = mapped_column(String(512), nullable=True)

    firma: Mapped[ResmiFirma] = relationship(back_populates="addresses")


class BkuRuhsat(Base):
    __tablename__ = "bku_ruhsatlar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    urun_adi: Mapped[str] = mapped_column(String(255), index=True)
    aktif_madde: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ruhsat_sahibi: Mapped[str] = mapped_column(String(255), index=True)
    formulasyon: Mapped[str | None] = mapped_column(String(64), nullable=True)


class BkuTavsiye(Base):
    __tablename__ = "bku_tavsiyeler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bitki: Mapped[str] = mapped_column(String(128), index=True)
    etmen: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    urun_adi: Mapped[str] = mapped_column(String(255), index=True)
    aktif_madde: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    il: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ilce: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    doz: Mapped[float | None] = mapped_column(Float, nullable=True)
