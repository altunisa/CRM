from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.crm import CrmFirmaZenginlestirme
from app.models.resmi import BkuRuhsat, ResmiFirma

CORP_SUFFIXES = {
    "A.S.",
    "AS",
    "AŞ",
    "A.Ş.",
    "LTD",
    "LTD.",
    "LTD STI",
    "LTD. STI.",
    "SAN",
    "TIC",
    "VE",
}


@dataclass
class RuhsatStats:
    ruhsat_sayisi: int
    aktif_madde_sayisi: int


def normalize_company_name(name: str | None) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^A-Z0-9ÇĞİÖŞÜ ]+", " ", name.upper())
    parts = [p for p in cleaned.split() if p and p not in CORP_SUFFIXES]
    return " ".join(parts).strip()


def _ruhsat_stats_query(normalized_name: str) -> Select[tuple[int, int]]:
    owner_norm = func.regexp_replace(func.upper(BkuRuhsat.ruhsat_sahibi), r"[^A-Z0-9ÇĞİÖŞÜ ]", "", "g")
    return select(
        func.count(BkuRuhsat.id),
        func.count(func.distinct(BkuRuhsat.aktif_madde)),
    ).where(owner_norm.contains(normalized_name))


def fetch_ruhsat_stats(db: Session, company_name: str) -> RuhsatStats:
    normalized = normalize_company_name(company_name)
    if not normalized:
        return RuhsatStats(0, 0)
    ruhsat_sayisi, aktif_madde_sayisi = db.execute(_ruhsat_stats_query(normalized)).one()
    return RuhsatStats(ruhsat_sayisi or 0, aktif_madde_sayisi or 0)


def classify_single_firm(db: Session, firma: ResmiFirma) -> CrmFirmaZenginlestirme:
    stats = fetch_ruhsat_stats(db, firma.company_name)
    enrich = db.get(CrmFirmaZenginlestirme, firma.gln) or CrmFirmaZenginlestirme(gln=firma.gln)

    enrich.ruhsat_sahibi = stats.ruhsat_sayisi > 0
    enrich.uretici = stats.aktif_madde_sayisi >= 4
    enrich.ithalatci = stats.aktif_madde_sayisi >= 2 and not enrich.uretici
    enrich.bayi = not enrich.ruhsat_sahibi
    enrich.toptanci = enrich.bayi and stats.ruhsat_sayisi == 0
    enrich.distributor = enrich.bayi and stats.aktif_madde_sayisi >= 1
    enrich.karma_firma = sum([enrich.ruhsat_sahibi, enrich.bayi, enrich.uretici, enrich.ithalatci]) >= 2

    enrich.firma_tipi_ana = (
        "ruhsat_sahibi" if enrich.ruhsat_sahibi else "kanal"
    )
    if enrich.ruhsat_sahibi:
        enrich.hedef_iliski_tipi = "portfoy_isbirligi" if stats.aktif_madde_sayisi < 5 else "rakip_izleme"
        enrich.firma_segment = "stratejik"
    elif enrich.bayi:
        enrich.hedef_iliski_tipi = "satis_kanali"
        enrich.firma_segment = "kanal"
    else:
        enrich.hedef_iliski_tipi = "takip"
        enrich.firma_segment = "standart"

    enrich.stratejik_skor = min(100.0, stats.ruhsat_sayisi * 3 + stats.aktif_madde_sayisi * 6)
    enrich.kanal_skor = 70.0 if enrich.bayi else 30.0
    enrich.operasyon_skor = 80.0 if enrich.karma_firma else 55.0

    enrich.siniflandirma_notu = (
        f"ruhsat={stats.ruhsat_sayisi}, aktif_madde={stats.aktif_madde_sayisi}, normalized_name={normalize_company_name(firma.company_name)}"
    )
    enrich.siniflandirma_kaynagi = "bku_ruhsatlar"
    enrich.siniflandirma_guncelleme_tarihi = datetime.utcnow()

    db.add(enrich)
    return enrich


def classify_all_firms(db: Session, limit: int = 500) -> int:
    firms = db.scalars(select(ResmiFirma).limit(limit)).all()
    for firma in firms:
        classify_single_firm(db, firma)
    db.commit()
    return len(firms)
