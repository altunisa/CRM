from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crm import CrmFirmaAktivitesi, CrmFirmaZenginlestirme
from app.models.resmi import ResmiFirma, ResmiFirmaAdresi

router = APIRouter()

FirmaTipiAna = Literal[
    "ruhsat_sahibi",
    "bayi",
    "toptanci",
    "distributor",
    "uretici",
    "ithalatci",
    "karma",
    "musteri_adayi",
    "belirsiz",
]

HedefIliskiTipi = Literal[
    "rakip_izleme",
    "bayi_adayi",
    "satis_kanali",
    "fason_adayi",
    "portfoy_isbirligi",
    "tedarikci_adayi",
    "musteri_adayi",
    "belirsiz",
]

SegmentTipi = Literal["A", "B", "C"]


class ClassificationPatchRequest(BaseModel):
    ruhsat_sahibi: Optional[bool] = None
    uretici: Optional[bool] = None
    ithalatci: Optional[bool] = None
    bayi: Optional[bool] = None
    toptanci: Optional[bool] = None
    distributor: Optional[bool] = None
    karma_firma: Optional[bool] = None
    firma_tipi_ana: Optional[FirmaTipiAna] = None
    hedef_iliski_tipi: Optional[HedefIliskiTipi] = None
    firma_segment: Optional[SegmentTipi] = None
    stratejik_skor: Optional[int] = None
    kanal_skor: Optional[int] = None
    operasyon_skor: Optional[int] = None
    siniflandirma_notu: Optional[str] = None
    siniflandirma_kaynagi: Optional[str] = "manual"


class BatchClassifyRequest(BaseModel):
    gln_list: Optional[list[str]] = None
    limit: int = 500
    source: str = "system"


def clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_text(value: Optional[str]) -> str:
    return (value or "").strip()


def ensure_enrichment_row(db: Session, gln: str) -> CrmFirmaZenginlestirme:
    row = db.query(CrmFirmaZenginlestirme).filter(CrmFirmaZenginlestirme.gln == gln).first()
    if not row:
        row = CrmFirmaZenginlestirme(gln=gln)
        db.add(row)
        db.flush()
    return row


def get_ruhsat_summary(db: Session, company_name: str) -> dict:
    sql = text(
        """
        SELECT
            COUNT(*)::int AS ruhsat_sayisi,
            COUNT(DISTINCT aktif_madde)::int AS aktif_madde_sayisi,
            MAX(ruhsat_tarihi) AS son_ruhsat_tarihi
        FROM bku_ruhsatlar
        WHERE firma = :company_name
           OR firma ILIKE :company_name_like
        """
    )
    row = db.execute(
        sql,
        {
            "company_name": company_name,
            "company_name_like": company_name.strip(),
        },
    ).mappings().first()

    if not row:
        return {"ruhsat_sayisi": 0, "aktif_madde_sayisi": 0, "son_ruhsat_tarihi": None}
    return dict(row)


def get_last_activity_info(db: Session, gln: str) -> dict:
    row = (
        db.query(CrmFirmaAktivitesi)
        .filter(CrmFirmaAktivitesi.gln == gln)
        .order_by(CrmFirmaAktivitesi.activity_date.desc(), CrmFirmaAktivitesi.id.desc())
        .first()
    )

    if not row:
        return {"son_aktivite_tarihi": None, "son_aktivite_gun": None}

    delta_days = (datetime.now() - row.activity_date).days if row.activity_date else None
    return {
        "son_aktivite_tarihi": row.activity_date,
        "son_aktivite_gun": delta_days,
    }


def derive_main_type(flags: dict) -> str:
    active = [
        k for k in ["ruhsat_sahibi", "uretici", "ithalatci", "bayi", "toptanci", "distributor"]
        if flags.get(k)
    ]
    if len(active) > 1:
        return "karma"
    if flags.get("ruhsat_sahibi"):
        return "ruhsat_sahibi"
    if flags.get("bayi"):
        return "bayi"
    if flags.get("toptanci"):
        return "toptanci"
    if flags.get("distributor"):
        return "distributor"
    if flags.get("uretici"):
        return "uretici"
    if flags.get("ithalatci"):
        return "ithalatci"
    return "musteri_adayi"


def derive_target_relation(flags: dict, ruhsat_sayisi: int) -> str:
    if flags.get("ruhsat_sahibi"):
        if flags.get("uretici"):
            return "fason_adayi"
        if ruhsat_sayisi >= 10:
            return "rakip_izleme"
        return "portfoy_isbirligi"

    if flags.get("bayi") or flags.get("distributor") or flags.get("toptanci"):
        return "satis_kanali"

    return "musteri_adayi"


def derive_scores(
    flags: dict,
    ruhsat_sayisi: int,
    aktif_madde_sayisi: int,
    son_aktivite_gun: Optional[int],
) -> dict:
    stratejik = 0
    kanal = 0
    operasyon = 20

    if flags.get("ruhsat_sahibi"):
        stratejik += 35
        stratejik += min(ruhsat_sayisi * 2, 35)
        stratejik += min(aktif_madde_sayisi * 2, 15)
    if flags.get("uretici"):
        stratejik += 10
    if flags.get("ithalatci"):
        stratejik += 10

    if flags.get("bayi"):
        kanal += 35
    if flags.get("distributor"):
        kanal += 30
    if flags.get("toptanci"):
        kanal += 20
    if flags.get("ruhsat_sahibi") and not (
        flags.get("bayi") or flags.get("distributor") or flags.get("toptanci")
    ):
        kanal += 5

    if son_aktivite_gun is None:
        operasyon += 45
    elif son_aktivite_gun >= 90:
        operasyon += 40
    elif son_aktivite_gun >= 45:
        operasyon += 30
    elif son_aktivite_gun >= 20:
        operasyon += 20
    else:
        operasyon += 5

    return {
        "stratejik_skor": clamp_score(stratejik),
        "kanal_skor": clamp_score(kanal),
        "operasyon_skor": clamp_score(operasyon),
    }


def derive_segment(scores: dict) -> str:
    top = max(scores["stratejik_skor"], scores["kanal_skor"], scores["operasyon_skor"])
    if top >= 75:
        return "A"
    if top >= 45:
        return "B"
    return "C"


def log_classification_change(
    db: Session,
    gln: str,
    eski_firma_tipi_ana: Optional[str],
    yeni_firma_tipi_ana: Optional[str],
    eski_hedef_iliski_tipi: Optional[str],
    yeni_hedef_iliski_tipi: Optional[str],
    source: str,
    note: Optional[str],
) -> None:
    db.execute(
        text(
            """
            INSERT INTO crm_firma_classification_logs (
                gln,
                eski_firma_tipi_ana,
                yeni_firma_tipi_ana,
                eski_hedef_iliski_tipi,
                yeni_hedef_iliski_tipi,
                source,
                note
            ) VALUES (
                :gln,
                :eski_firma_tipi_ana,
                :yeni_firma_tipi_ana,
                :eski_hedef_iliski_tipi,
                :yeni_hedef_iliski_tipi,
                :source,
                :note
            )
            """
        ),
        {
            "gln": gln,
            "eski_firma_tipi_ana": eski_firma_tipi_ana,
            "yeni_firma_tipi_ana": yeni_firma_tipi_ana,
            "eski_hedef_iliski_tipi": eski_hedef_iliski_tipi,
            "yeni_hedef_iliski_tipi": yeni_hedef_iliski_tipi,
            "source": source,
            "note": note,
        },
    )


def classify_single_company(db: Session, gln: str, source: str = "system") -> dict:
    firma = db.query(ResmiFirma).filter(ResmiFirma.gln == gln).first()
    if not firma:
        raise HTTPException(status_code=404, detail=f"Firma bulunamadı: {gln}")

    enrichment = ensure_enrichment_row(db, gln)
    activity_info = get_last_activity_info(db, gln)
    ruhsat_ozeti = get_ruhsat_summary(db, normalize_text(firma.company_name))

    raw_text = f"{normalize_text(getattr(firma, 'company_type', ''))} {normalize_text(getattr(firma, 'company_title', ''))}"
    raw_upper = raw_text.upper()

    flags = {
        "ruhsat_sahibi": (ruhsat_ozeti.get("ruhsat_sayisi") or 0) > 0,
        "uretici": ("ÜRET" in raw_upper) or ("URET" in raw_upper) or bool(getattr(enrichment, "uretici", False)),
        "ithalatci": ("İTHALAT" in raw_upper) or ("ITHALAT" in raw_upper) or bool(getattr(enrichment, "ithalatci", False)),
        "bayi": ("BAYİ" in raw_upper) or ("BAYI" in raw_upper) or bool(getattr(enrichment, "bayi", False)),
        "toptanci": ("TOPTAN" in raw_upper) or bool(getattr(enrichment, "toptanci", False)),
        "distributor": ("DISTR" in raw_upper) or bool(getattr(enrichment, "distributor", False)),
    }
    flags["karma_firma"] = sum(1 for v in flags.values() if v) > 1

    main_type = derive_main_type(flags)
    target_relation = derive_target_relation(flags, ruhsat_ozeti.get("ruhsat_sayisi") or 0)
    scores = derive_scores(
        flags,
        ruhsat_ozeti.get("ruhsat_sayisi") or 0,
        ruhsat_ozeti.get("aktif_madde_sayisi") or 0,
        activity_info.get("son_aktivite_gun"),
    )
    segment = derive_segment(scores)

    old_type = getattr(enrichment, "firma_tipi_ana", None)
    old_target = getattr(enrichment, "hedef_iliski_tipi", None)

    enrichment.ruhsat_sahibi = flags["ruhsat_sahibi"]
    enrichment.uretici = flags["uretici"]
    enrichment.ithalatci = flags["ithalatci"]
    enrichment.bayi = flags["bayi"]
    enrichment.toptanci = flags["toptanci"]
    enrichment.distributor = flags["distributor"]
    enrichment.karma_firma = flags["karma_firma"]
    enrichment.firma_tipi_ana = main_type
    enrichment.hedef_iliski_tipi = target_relation
    enrichment.firma_segment = segment
    enrichment.stratejik_skor = scores["stratejik_skor"]
    enrichment.kanal_skor = scores["kanal_skor"]
    enrichment.operasyon_skor = scores["operasyon_skor"]
    enrichment.siniflandirma_notu = (
        f"Auto classify | ruhsat={ruhsat_ozeti.get('ruhsat_sayisi', 0)} | "
        f"aktif_madde={ruhsat_ozeti.get('aktif_madde_sayisi', 0)} | "
        f"son_aktivite_gun={activity_info.get('son_aktivite_gun')}"
    )
    enrichment.siniflandirma_kaynagi = source
    enrichment.siniflandirma_guncelleme_tarihi = datetime.now()

    log_classification_change(
        db=db,
        gln=gln,
        eski_firma_tipi_ana=old_type,
        yeni_firma_tipi_ana=main_type,
        eski_hedef_iliski_tipi=old_target,
        yeni_hedef_iliski_tipi=target_relation,
        source=source,
        note=enrichment.siniflandirma_notu,
    )

    return {
        "gln": gln,
        "firma_adi": firma.company_name,
        "firma_tipi_ana": main_type,
        "hedef_iliski_tipi": target_relation,
        "firma_segment": segment,
        "skorlar": scores,
        "ruhsat_ozeti": ruhsat_ozeti,
        "aktivite_ozeti": activity_info,
    }


@router.get("")
def list_firms(
    q: Optional[str] = Query(None),
    il: Optional[str] = Query(None),
    ilce: Optional[str] = Query(None),
    firma_tipi: Optional[str] = Query(None),
    hedef_iliski_tipi: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    ruhsat_sahibi: Optional[bool] = Query(None),
    bayi: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == ResmiFirma.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln)
    )

    if q:
        query = query.filter(ResmiFirma.company_name.ilike(f"%{q}%"))
    if il:
        query = query.filter(ResmiFirmaAdresi.il == il)
    if ilce:
        query = query.filter(ResmiFirmaAdresi.ilce == ilce)
    if firma_tipi:
        query = query.filter(CrmFirmaZenginlestirme.firma_tipi_ana == firma_tipi)
    if hedef_iliski_tipi:
        query = query.filter(CrmFirmaZenginlestirme.hedef_iliski_tipi == hedef_iliski_tipi)
    if segment:
        query = query.filter(CrmFirmaZenginlestirme.firma_segment == segment)
    if ruhsat_sahibi is not None:
        query = query.filter(CrmFirmaZenginlestirme.ruhsat_sahibi == ruhsat_sahibi)
    if bayi is not None:
        query = query.filter(CrmFirmaZenginlestirme.bayi == bayi)

    rows = query.order_by(ResmiFirma.company_name.asc()).limit(limit).all()

    items = []
    for f, a, e in rows:
        items.append(
            {
                "gln": f.gln,
                "firma_adi": f.company_name,
                "firma_unvani": getattr(f, "company_title", None),
                "company_type": getattr(f, "company_type", None),
                "il": a.il,
                "ilce": a.ilce,
                "adres": a.adres,
                "adres_tipi": a.address_type,
                "firma_tipi_ana": getattr(e, "firma_tipi_ana", None) if e else None,
                "hedef_iliski_tipi": getattr(e, "hedef_iliski_tipi", None) if e else None,
                "firma_segment": getattr(e, "firma_segment", None) if e else None,
                "ruhsat_sahibi": getattr(e, "ruhsat_sahibi", False) if e else False,
                "uretici": getattr(e, "uretici", False) if e else False,
                "ithalatci": getattr(e, "ithalatci", False) if e else False,
                "bayi": getattr(e, "bayi", False) if e else False,
                "toptanci": getattr(e, "toptanci", False) if e else False,
                "distributor": getattr(e, "distributor", False) if e else False,
                "karma_firma": getattr(e, "karma_firma", False) if e else False,
                "stratejik_skor": getattr(e, "stratejik_skor", 0) if e else 0,
                "kanal_skor": getattr(e, "kanal_skor", 0) if e else 0,
                "operasyon_skor": getattr(e, "operasyon_skor", 0) if e else 0,
                "telefon_mobil": getattr(e, "phone_mobile", None) if e else None,
                "telefon_ofis": getattr(e, "phone_office", None) if e else None,
                "yetkili_kisi": getattr(e, "authorized_person", None) if e else None,
                "durum": getattr(e, "enrichment_status", None) if e else None,
            }
        )

    return {"items": items, "count": len(items)}


@router.get("/top/list")
def get_top_firms(
    score_type: Literal["stratejik", "kanal", "operasyon"] = Query("operasyon"),
    firma_tipi: Optional[str] = Query(None),
    hedef_iliski_tipi: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    score_col = {
        "stratejik": CrmFirmaZenginlestirme.stratejik_skor,
        "kanal": CrmFirmaZenginlestirme.kanal_skor,
        "operasyon": CrmFirmaZenginlestirme.operasyon_skor,
    }[score_type]

    query = (
        db.query(ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == ResmiFirma.gln)
    )

    if firma_tipi:
        query = query.filter(CrmFirmaZenginlestirme.firma_tipi_ana == firma_tipi)
    if hedef_iliski_tipi:
        query = query.filter(CrmFirmaZenginlestirme.hedef_iliski_tipi == hedef_iliski_tipi)

    rows = query.order_by(score_col.desc(), ResmiFirma.company_name.asc()).limit(limit).all()

    return {
        "score_type": score_type,
        "count": len(rows),
        "items": [
            {
                "gln": f.gln,
                "firma_adi": f.company_name,
                "il": a.il,
                "ilce": a.ilce,
                "firma_tipi_ana": e.firma_tipi_ana if e else None,
                "hedef_iliski_tipi": e.hedef_iliski_tipi if e else None,
                "firma_segment": e.firma_segment if e else None,
                "stratejik_skor": e.stratejik_skor if e else 0,
                "kanal_skor": e.kanal_skor if e else 0,
                "operasyon_skor": e.operasyon_skor if e else 0,
            }
            for f, a, e in rows
        ],
    }


@router.get("/{gln}/scores")
def get_scores(gln: str, db: Session = Depends(get_db)):
    enrichment = db.query(CrmFirmaZenginlestirme).filter(CrmFirmaZenginlestirme.gln == gln).first()
    if not enrichment:
        raise HTTPException(status_code=404, detail="Bu GLN için enrichment/sınıflandırma kaydı yok")

    return {
        "gln": gln,
        "stratejik_skor": getattr(enrichment, "stratejik_skor", 0),
        "kanal_skor": getattr(enrichment, "kanal_skor", 0),
        "operasyon_skor": getattr(enrichment, "operasyon_skor", 0),
    }


@router.get("/{gln}")
def get_firm_detail(gln: str, db: Session = Depends(get_db)):
    row = (
        db.query(ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == ResmiFirma.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln)
        .filter(ResmiFirma.gln == gln)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")

    f, a, e = row
    ruhsat_ozeti = get_ruhsat_summary(db, normalize_text(f.company_name))
    activities = (
        db.query(CrmFirmaAktivitesi)
        .filter(CrmFirmaAktivitesi.gln == gln)
        .order_by(CrmFirmaAktivitesi.activity_date.desc(), CrmFirmaAktivitesi.id.desc())
        .limit(20)
        .all()
    )

    return {
        "gln": f.gln,
        "firma_adi": f.company_name,
        "firma_unvani": getattr(f, "company_title", None),
        "company_type": getattr(f, "company_type", None),
        "is_active": getattr(f, "is_active", None),
        "il": a.il,
        "ilce": a.ilce,
        "adres": a.adres,
        "adres_tipi": a.address_type,
        "siniflandirma": {
            "firma_tipi_ana": getattr(e, "firma_tipi_ana", None) if e else None,
            "hedef_iliski_tipi": getattr(e, "hedef_iliski_tipi", None) if e else None,
            "firma_segment": getattr(e, "firma_segment", None) if e else None,
            "ruhsat_sahibi": getattr(e, "ruhsat_sahibi", False) if e else False,
            "uretici": getattr(e, "uretici", False) if e else False,
            "ithalatci": getattr(e, "ithalatci", False) if e else False,
            "bayi": getattr(e, "bayi", False) if e else False,
            "toptanci": getattr(e, "toptanci", False) if e else False,
            "distributor": getattr(e, "distributor", False) if e else False,
            "karma_firma": getattr(e, "karma_firma", False) if e else False,
            "stratejik_skor": getattr(e, "stratejik_skor", 0) if e else 0,
            "kanal_skor": getattr(e, "kanal_skor", 0) if e else 0,
            "operasyon_skor": getattr(e, "operasyon_skor", 0) if e else 0,
            "siniflandirma_notu": getattr(e, "siniflandirma_notu", None) if e else None,
            "siniflandirma_kaynagi": getattr(e, "siniflandirma_kaynagi", None) if e else None,
            "siniflandirma_guncelleme_tarihi": (
                getattr(e, "siniflandirma_guncelleme_tarihi", None).isoformat()
                if e and getattr(e, "siniflandirma_guncelleme_tarihi", None)
                else None
            ),
        },
        "iletisim": {
            "telefon_mobil": getattr(e, "phone_mobile", None) if e else None,
            "telefon_ofis": getattr(e, "phone_office", None) if e else None,
            "email": getattr(e, "email_marketing", None) if e else None,
            "yetkili_kisi": getattr(e, "authorized_person", None) if e else None,
            "yetkili_unvan": getattr(e, "authorized_title", None) if e else None,
            "durum": getattr(e, "enrichment_status", None) if e else None,
        },
        "ruhsat_ozeti": ruhsat_ozeti,
        "aktiviteler": [
            {
                "id": x.id,
                "activity_type": x.activity_type,
                "activity_date": x.activity_date.isoformat() if x.activity_date else None,
                "result": x.result,
                "note": x.note,
                "created_by": x.created_by,
                "next_action_date": x.next_action_date.isoformat() if x.next_action_date else None,
            }
            for x in activities
        ],
    }


@router.post("/classify")
def batch_classify_firms(payload: BatchClassifyRequest, db: Session = Depends(get_db)):
    if payload.gln_list:
        firms = db.query(ResmiFirma).filter(ResmiFirma.gln.in_(payload.gln_list)).all()
    else:
        firms = db.query(ResmiFirma).order_by(ResmiFirma.company_name.asc()).limit(payload.limit).all()

    results = []
    for firm in firms:
        results.append(classify_single_company(db, firm.gln, source=payload.source))

    db.commit()
    return {
        "ok": True,
        "total_processed": len(results),
        "items": results,
    }


@router.post("/{gln}/classify")
def classify_one_firm(gln: str, db: Session = Depends(get_db)):
    result = classify_single_company(db, gln, source="manual_single")
    db.commit()
    return result


@router.patch("/{gln}/classification")
def patch_classification(gln: str, payload: ClassificationPatchRequest, db: Session = Depends(get_db)):
    firma = db.query(ResmiFirma).filter(ResmiFirma.gln == gln).first()
    if not firma:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")

    enrichment = ensure_enrichment_row(db, gln)
    old_type = getattr(enrichment, "firma_tipi_ana", None)
    old_target = getattr(enrichment, "hedef_iliski_tipi", None)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Güncellenecek alan yok")

    for key, value in data.items():
        setattr(enrichment, key, value)

    enrichment.siniflandirma_guncelleme_tarihi = datetime.now()

    log_classification_change(
        db=db,
        gln=gln,
        eski_firma_tipi_ana=old_type,
        yeni_firma_tipi_ana=data.get("firma_tipi_ana", old_type),
        eski_hedef_iliski_tipi=old_target,
        yeni_hedef_iliski_tipi=data.get("hedef_iliski_tipi", old_target),
        source=data.get("siniflandirma_kaynagi", "manual"),
        note=data.get("siniflandirma_notu", "Manual classification patch"),
    )

    db.commit()
    return {"ok": True, "gln": gln, "updated_fields": list(data.keys())}