from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResmiFirma(Base):
    __tablename__ = "resmi_firmalar"

    gln: Mapped[str] = mapped_column(String(32), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_title: Mapped[str | None] = mapped_column(String(255))
    company_type: Mapped[str | None] = mapped_column(String(100))
    tax_no: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_system: Mapped[str] = mapped_column(String(50), default="BKST")
    source_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    raw_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    addresses: Mapped[list["ResmiFirmaAdresi"]] = relationship(
        "ResmiFirmaAdresi",
        back_populates="firma",
        cascade="all, delete-orphan"
    )
    enrichment: Mapped["CrmFirmaZenginlestirme | None"] = relationship(
        "CrmFirmaZenginlestirme",
        back_populates="firma",
        uselist=False
    )
    targeting: Mapped[list["CrmUrunHedefleme"]] = relationship(
        "CrmUrunHedefleme",
        back_populates="firma",
        cascade="all, delete-orphan"
    )
    aktiviteler: Mapped[list["CrmFirmaAktivitesi"]] = relationship(
        "CrmFirmaAktivitesi",
        back_populates="firma",
        cascade="all, delete-orphan",
        order_by="desc(CrmFirmaAktivitesi.activity_date)"
    )


class ResmiFirmaAdresi(Base):
    __tablename__ = "resmi_firma_adresleri"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gln: Mapped[str] = mapped_column(
        ForeignKey("resmi_firmalar.gln", ondelete="CASCADE"),
        nullable=False
    )
    address_type: Mapped[str | None] = mapped_column(String(50))
    il: Mapped[str | None] = mapped_column(String(100))
    ilce: Mapped[str | None] = mapped_column(String(100))
    mahalle: Mapped[str | None] = mapped_column(String(100))
    posta_kodu: Mapped[str | None] = mapped_column(String(20))
    adres: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    maps_place_id: Mapped[str | None] = mapped_column(String(128))
    raw_json: Mapped[dict | None] = mapped_column(JSONB)
    source_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    firma: Mapped["ResmiFirma"] = relationship(
        "ResmiFirma",
        back_populates="addresses"
    )