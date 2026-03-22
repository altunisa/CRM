from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from sqlalchemy import Column, Boolean, Integer, String, Text, DateTime

# CrmFirmaZenginlestirme sınıfı içine EKLEYİN

class CrmFirmaZenginlestirme(Base):
    __tablename__ = "crm_firma_zenginlestirme"

    gln: Mapped[str] = mapped_column(
        ForeignKey("resmi_firmalar.gln", ondelete="CASCADE"),
        primary_key=True
    )
    phone_mobile: Mapped[str | None] = mapped_column(String(50))
    phone_office: Mapped[str | None] = mapped_column(String(50))
    email_marketing: Mapped[str | None] = mapped_column(String(255))
    authorized_person: Mapped[str | None] = mapped_column(String(255))
    authorized_title: Mapped[str | None] = mapped_column(String(255))
    annual_potential_volume: Mapped[float | None] = mapped_column(Numeric(18, 2))
    current_competitor_brands: Mapped[str | None] = mapped_column(Text)
    customer_note: Mapped[str | None] = mapped_column(Text)
    ruhsat_sahibi = Column(Boolean, default=False)
    uretici = Column(Boolean, default=False)
    ithalatci = Column(Boolean, default=False)
    bayi = Column(Boolean, default=False)
    toptanci = Column(Boolean, default=False)
    distributor = Column(Boolean, default=False)
    karma_firma = Column(Boolean, default=False)

    firma_tipi_ana = Column(String(50), nullable=True)
    hedef_iliski_tipi = Column(String(50), nullable=True)
    firma_segment = Column(String(10), nullable=True)

    stratejik_skor = Column(Integer, default=0)
    kanal_skor = Column(Integer, default=0)
    operasyon_skor = Column(Integer, default=0)

    siniflandirma_notu = Column(Text, nullable=True)
    siniflandirma_kaynagi = Column(String(30), nullable=True)
    siniflandirma_guncelleme_tarihi = Column(DateTime, nullable=True)
    enrichment_status: Mapped[str | None] = mapped_column(String(30))
    last_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_contact_result: Mapped[str | None] = mapped_column(String(100))
    next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    enriched_by: Mapped[str | None] = mapped_column(String(100))
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    firma: Mapped["ResmiFirma"] = relationship(
        "ResmiFirma",
        back_populates="enrichment"
    )


class CrmUrunProfili(Base):
    __tablename__ = "crm_urun_profilleri"

    urun_kodu: Mapped[str] = mapped_column(String(100), primary_key=True)
    urun_adi: Mapped[str] = mapped_column(String(255), nullable=False)
    kategori_skor_map: Mapped[dict | None] = mapped_column(JSONB)
    il_skor_map: Mapped[dict | None] = mapped_column(JSONB)
    ilce_skor_map: Mapped[dict | None] = mapped_column(JSONB)
    adres_tipi_skor_map: Mapped[dict | None] = mapped_column(JSONB)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    targetings: Mapped[list["CrmUrunHedefleme"]] = relationship(
        "CrmUrunHedefleme",
        back_populates="urun_profili",
        cascade="all, delete-orphan"
    )


class CrmUrunHedefleme(Base):
    __tablename__ = "crm_urun_hedefleme"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gln: Mapped[str] = mapped_column(
        ForeignKey("resmi_firmalar.gln", ondelete="CASCADE"),
        nullable=False
    )
    urun_kodu: Mapped[str] = mapped_column(
        ForeignKey("crm_urun_profilleri.urun_kodu", ondelete="CASCADE"),
        nullable=False
    )
    urun_adi: Mapped[str | None] = mapped_column(String(255))
    hedef_il: Mapped[str | None] = mapped_column(String(100))
    hedef_ilce: Mapped[str | None] = mapped_column(String(100))
    konum_skoru: Mapped[int] = mapped_column(default=0)
    kategori_skoru: Mapped[int] = mapped_column(default=0)
    adres_tipi_skoru: Mapped[int] = mapped_column(default=0)
    potansiyel_skoru: Mapped[int] = mapped_column(default=0)
    toplam_skor: Mapped[int] = mapped_column(default=0)
    oncelik_sinifi: Mapped[str | None] = mapped_column(String(1))
    score_explain: Mapped[dict | None] = mapped_column(JSONB)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    firma: Mapped["ResmiFirma"] = relationship(
        "ResmiFirma",
        back_populates="targeting"
    )
    urun_profili: Mapped["CrmUrunProfili"] = relationship(
        "CrmUrunProfili",
        back_populates="targetings"
    )


class CrmFirmaAktivitesi(Base):
    __tablename__ = "crm_firma_aktiviteleri"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gln: Mapped[str] = mapped_column(
        ForeignKey("resmi_firmalar.gln", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    activity_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    result: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(100))
    next_action_date: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    firma: Mapped["ResmiFirma"] = relationship(
        "ResmiFirma",
        back_populates="aktiviteler"
    )