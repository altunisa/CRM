from io import BytesIO
from typing import Optional
from datetime import date, datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, cast, func, Date
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.crm import (
    CrmUrunHedefleme,
    CrmFirmaZenginlestirme,
    CrmFirmaAktivitesi,
)
from app.models.resmi import ResmiFirma, ResmiFirmaAdresi

router = APIRouter()


class EnrichmentPayload(BaseModel):
    gln: str
    telefon_mobil: Optional[str] = None
    telefon_ofis: Optional[str] = None
    email: Optional[EmailStr] = None
    yetkili_kisi: Optional[str] = None
    yetkili_unvan: Optional[str] = None
    rakip_marka: Optional[str] = None
    musteri_notu: Optional[str] = None
    yillik_potansiyel_hacim: Optional[float] = None
    durum: Optional[str] = None
    last_contact_date: Optional[date] = None
    last_contact_result: Optional[str] = None
    next_visit_date: Optional[date] = None


class ActivityCreate(BaseModel):
    gln: str
    activity_type: str
    activity_date: datetime
    result: str | None = None
    note: str | None = None
    created_by: str | None = None
    next_action_date: datetime | None = None


class ActivityOut(BaseModel):
    id: int
    gln: str
    activity_type: str
    activity_date: datetime
    result: str | None = None
    note: str | None = None
    created_by: str | None = None
    next_action_date: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/targets")
def get_targets(
    urun_kodu: str,
    oncelik: str = "A",
    il: str | None = None,
    ilce: str | None = None,
    firma_tipi: str | None = None,
    adres_tipi: str | None = None,
    durum: str | None = None,
    not_var: bool | None = None,
    min_skor: int | None = None,
    min_potansiyel: float | None = None,
    max_potansiyel: float | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = (
        db.query(CrmUrunHedefleme, ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirma, ResmiFirma.gln == CrmUrunHedefleme.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == CrmUrunHedefleme.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == CrmUrunHedefleme.gln)
        .filter(
            CrmUrunHedefleme.urun_kodu == urun_kodu,
            CrmUrunHedefleme.oncelik_sinifi == oncelik,
        )
    )

    if il:
        query = query.filter(CrmUrunHedefleme.hedef_il == il)

    if ilce:
        query = query.filter(CrmUrunHedefleme.hedef_ilce == ilce)

    if firma_tipi:
        query = query.filter(ResmiFirma.company_type == firma_tipi)

    if adres_tipi:
        query = query.filter(ResmiFirmaAdresi.address_type == adres_tipi)

    if min_skor is not None:
        query = query.filter(CrmUrunHedefleme.toplam_skor >= min_skor)

    if durum:
        query = query.filter(CrmFirmaZenginlestirme.enrichment_status == durum)

    if not_var is True:
        query = query.filter(
            CrmFirmaZenginlestirme.customer_note.isnot(None),
            CrmFirmaZenginlestirme.customer_note != ""
        )
    elif not_var is False:
        query = query.filter(
            (CrmFirmaZenginlestirme.customer_note.is_(None)) |
            (CrmFirmaZenginlestirme.customer_note == "")
        )

    if min_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume >= min_potansiyel
        )

    if max_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume <= max_potansiyel
        )

    results = query.order_by(CrmUrunHedefleme.toplam_skor.desc()).limit(limit).all()

    return [
        {
            "gln": h.gln,
            "firma_adi": f.company_name,
            "urun_kodu": h.urun_kodu,
            "urun_adi": h.urun_adi,
            "il": a.il,
            "ilce": a.ilce,
            "adres": a.adres,
            "firma_tipi": f.company_type,
            "adres_tipi": a.address_type,
            "telefon_mobil": e.phone_mobile if e else None,
            "telefon_ofis": e.phone_office if e else None,
            "email": e.email_marketing if e else None,
            "yetkili": e.authorized_person if e else None,
            "yetkili_unvan": e.authorized_title if e else None,
            "potansiyel_hacim": float(e.annual_potential_volume) if e and e.annual_potential_volume is not None else None,
            "rakip_marka": e.current_competitor_brands if e else None,
            "musteri_notu": e.customer_note if e else None,
            "durum": e.enrichment_status if e else None,
            "last_contact_date": e.last_contact_date.isoformat() if e and e.last_contact_date else None,
            "last_contact_result": e.last_contact_result if e else None,
            "next_visit_date": e.next_visit_date.isoformat() if e and e.next_visit_date else None,
            "skor": h.toplam_skor,
            "oncelik": h.oncelik_sinifi,
        }
        for (h, f, a, e) in results
    ]


@router.get("/stats")
def get_stats(
    urun_kodu: str,
    db: Session = Depends(get_db),
):
    priority_stats = (
        db.query(
            CrmUrunHedefleme.oncelik_sinifi,
            func.count().label("adet")
        )
        .filter(CrmUrunHedefleme.urun_kodu == urun_kodu)
        .group_by(CrmUrunHedefleme.oncelik_sinifi)
        .all()
    )

    city_stats = (
        db.query(
            CrmUrunHedefleme.hedef_il,
            func.count().label("adet")
        )
        .filter(CrmUrunHedefleme.urun_kodu == urun_kodu)
        .group_by(CrmUrunHedefleme.hedef_il)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )

    type_stats = (
        db.query(
            ResmiFirma.company_type,
            func.count().label("adet")
        )
        .join(CrmUrunHedefleme, ResmiFirma.gln == CrmUrunHedefleme.gln)
        .filter(CrmUrunHedefleme.urun_kodu == urun_kodu)
        .group_by(ResmiFirma.company_type)
        .all()
    )

    return {
        "oncelik_dagilimi": [
            {"oncelik": x.oncelik_sinifi, "adet": x.adet}
            for x in priority_stats
        ],
        "il_dagilimi_top10": [
            {"il": x.hedef_il, "adet": x.adet}
            for x in city_stats
        ],
        "firma_tipi_dagilimi": [
            {"tip": x.company_type, "adet": x.adet}
            for x in type_stats
        ]
    }


@router.get("/targets/export")
def export_targets(
    urun_kodu: str,
    oncelik: str = "A",
    il: str | None = None,
    ilce: str | None = None,
    firma_tipi: str | None = None,
    adres_tipi: str | None = None,
    durum: str | None = None,
    not_var: bool | None = None,
    min_skor: int | None = None,
    min_potansiyel: float | None = None,
    max_potansiyel: float | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(CrmUrunHedefleme, ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirma, ResmiFirma.gln == CrmUrunHedefleme.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == CrmUrunHedefleme.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == CrmUrunHedefleme.gln)
        .filter(
            CrmUrunHedefleme.urun_kodu == urun_kodu,
            CrmUrunHedefleme.oncelik_sinifi == oncelik,
        )
    )

    if il:
        query = query.filter(CrmUrunHedefleme.hedef_il == il)

    if ilce:
        query = query.filter(CrmUrunHedefleme.hedef_ilce == ilce)

    if firma_tipi:
        query = query.filter(ResmiFirma.company_type == firma_tipi)

    if adres_tipi:
        query = query.filter(ResmiFirmaAdresi.address_type == adres_tipi)

    if min_skor is not None:
        query = query.filter(CrmUrunHedefleme.toplam_skor >= min_skor)

    if durum:
        query = query.filter(CrmFirmaZenginlestirme.enrichment_status == durum)

    if not_var is True:
        query = query.filter(
            CrmFirmaZenginlestirme.customer_note.isnot(None),
            CrmFirmaZenginlestirme.customer_note != ""
        )
    elif not_var is False:
        query = query.filter(
            (CrmFirmaZenginlestirme.customer_note.is_(None)) |
            (CrmFirmaZenginlestirme.customer_note == "")
        )

    if min_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume >= min_potansiyel
        )

    if max_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume <= max_potansiyel
        )

    results = query.order_by(CrmUrunHedefleme.toplam_skor.desc()).all()

    rows = [
        {
            "GLN": h.gln,
            "Firma Adı": f.company_name,
            "Ürün Kodu": h.urun_kodu,
            "Ürün Adı": h.urun_adi,
            "İl": a.il,
            "İlçe": a.ilce,
            "Adres": a.adres,
            "Firma Tipi": f.company_type,
            "Adres Tipi": a.address_type,
            "Telefon Mobil": e.phone_mobile if e else None,
            "Telefon Ofis": e.phone_office if e else None,
            "E-Posta": e.email_marketing if e else None,
            "Yetkili Kişi": e.authorized_person if e else None,
            "Yetkili Ünvan": e.authorized_title if e else None,
            "Yıllık Potansiyel Hacim": float(e.annual_potential_volume) if e and e.annual_potential_volume is not None else None,
            "Rakip Marka": e.current_competitor_brands if e else None,
            "Müşteri Notu": e.customer_note if e else None,
            "Durum": e.enrichment_status if e else None,
            "Son Görüşme Tarihi": e.last_contact_date.isoformat() if e and e.last_contact_date else None,
            "Son Görüşme Sonucu": e.last_contact_result if e else None,
            "Sonraki Ziyaret Tarihi": e.next_visit_date.isoformat() if e and e.next_visit_date else None,
            "Skor": h.toplam_skor,
            "Öncelik": h.oncelik_sinifi,
        }
        for (h, f, a, e) in results
    ]

    df = pd.DataFrame(rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Hedefler", index=False)

    output.seek(0)

    il_part = il if il else "TUM_ILLER"
    ilce_part = ilce if ilce else "TUM_ILCELER"
    firma_part = firma_tipi if firma_tipi else "TUM_FIRMALAR"
    filename = f"hedef_musteriler_{urun_kodu}_{oncelik}_{il_part}_{ilce_part}_{firma_part}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/enrich/{gln}")
def get_enrichment(gln: str, db: Session = Depends(get_db)):
    base = (
        db.query(ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == ResmiFirma.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln)
        .filter(ResmiFirma.gln == gln)
        .first()
    )

    if not base:
        raise HTTPException(status_code=404, detail="GLN bulunamadı")

    f, a, e = base

    if e:
        return {
            "found": True,
            "data": {
                "gln": f.gln,
                "firma_adi": f.company_name,
                "il": a.il,
                "ilce": a.ilce,
                "mahalle": getattr(a, "mahalle", None),
                "adres": a.adres,
                "telefon_mobil": e.phone_mobile,
                "telefon_ofis": e.phone_office,
                "email": e.email_marketing,
                "yetkili_kisi": e.authorized_person,
                "yetkili_unvan": e.authorized_title,
                "rakip_marka": e.current_competitor_brands,
                "musteri_notu": e.customer_note,
                "yillik_potansiyel_hacim": float(e.annual_potential_volume) if e.annual_potential_volume is not None else 0,
                "durum": e.enrichment_status,
                "last_contact_date": e.last_contact_date.isoformat() if e.last_contact_date else None,
                "last_contact_result": e.last_contact_result,
                "next_visit_date": e.next_visit_date.isoformat() if e.next_visit_date else None,
            }
        }

    return {
        "found": False,
        "base": {
            "gln": f.gln,
            "firma_adi": f.company_name,
            "il": a.il,
            "ilce": a.ilce,
            "mahalle": getattr(a, "mahalle", None),
            "adres": a.adres,
            "firma_tipi": f.company_type,
            "adres_tipi": a.address_type,
        }
    }


@router.post("/enrich")
def save_enrichment(payload: EnrichmentPayload, db: Session = Depends(get_db)):
    firma = db.query(ResmiFirma).filter(ResmiFirma.gln == payload.gln).first()
    if not firma:
        raise HTTPException(status_code=404, detail="Bu GLN resmi_firmalar tablosunda yok")

    row = (
        db.query(CrmFirmaZenginlestirme)
        .filter(CrmFirmaZenginlestirme.gln == payload.gln)
        .first()
    )

    if not row:
        row = CrmFirmaZenginlestirme(gln=payload.gln)
        db.add(row)

    row.phone_mobile = payload.telefon_mobil
    row.phone_office = payload.telefon_ofis
    row.email_marketing = payload.email
    row.authorized_person = payload.yetkili_kisi
    row.authorized_title = payload.yetkili_unvan
    row.current_competitor_brands = payload.rakip_marka
    row.customer_note = payload.musteri_notu
    row.annual_potential_volume = payload.yillik_potansiyel_hacim
    row.enrichment_status = payload.durum
    row.last_contact_date = payload.last_contact_date
    row.last_contact_result = payload.last_contact_result
    row.next_visit_date = payload.next_visit_date

    db.commit()
    db.refresh(row)

    return {
        "ok": True,
        "message": "Enrichment kaydı başarıyla kaydedildi",
        "gln": payload.gln
    }


@router.get("/enrich-search")
def search_for_enrichment(
    urun_kodu: Optional[str] = None,
    oncelik: Optional[str] = None,
    il: Optional[str] = None,
    ilce: Optional[str] = None,
    firma_tipi: Optional[str] = None,
    adres_tipi: Optional[str] = None,
    durum: Optional[str] = None,
    not_var: Optional[bool] = None,
    min_skor: Optional[float] = None,
    min_potansiyel: Optional[float] = None,
    max_potansiyel: Optional[float] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = (
        db.query(CrmUrunHedefleme, ResmiFirma, ResmiFirmaAdresi, CrmFirmaZenginlestirme)
        .join(ResmiFirma, ResmiFirma.gln == CrmUrunHedefleme.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == CrmUrunHedefleme.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == CrmUrunHedefleme.gln)
    )

    if urun_kodu:
        query = query.filter(CrmUrunHedefleme.urun_kodu == urun_kodu)

    if oncelik:
        query = query.filter(CrmUrunHedefleme.oncelik_sinifi == oncelik)

    if il:
        query = query.filter(CrmUrunHedefleme.hedef_il == il)

    if ilce:
        query = query.filter(CrmUrunHedefleme.hedef_ilce == ilce)

    if firma_tipi:
        query = query.filter(ResmiFirma.company_type == firma_tipi)

    if adres_tipi:
        query = query.filter(ResmiFirmaAdresi.address_type == adres_tipi)

    if min_skor is not None:
        query = query.filter(CrmUrunHedefleme.toplam_skor >= min_skor)

    if durum:
        query = query.filter(CrmFirmaZenginlestirme.enrichment_status == durum)

    if not_var is True:
        query = query.filter(
            CrmFirmaZenginlestirme.customer_note.isnot(None),
            CrmFirmaZenginlestirme.customer_note != ""
        )
    elif not_var is False:
        query = query.filter(
            (CrmFirmaZenginlestirme.customer_note.is_(None)) |
            (CrmFirmaZenginlestirme.customer_note == "")
        )

    if min_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume >= min_potansiyel
        )

    if max_potansiyel is not None:
        query = query.filter(
            CrmFirmaZenginlestirme.annual_potential_volume.isnot(None),
            CrmFirmaZenginlestirme.annual_potential_volume <= max_potansiyel
        )

    results = query.order_by(
        CrmUrunHedefleme.toplam_skor.desc(),
        ResmiFirma.company_name.asc()
    ).limit(limit).all()

    items = [
        {
            "gln": h.gln,
            "firma_adi": f.company_name,
            "firma_tipi": f.company_type,
            "adres_tipi": a.address_type,
            "il": a.il,
            "ilce": a.ilce,
            "mahalle": getattr(a, "mahalle", None),
            "adres": a.adres,
            "urun_kodu": h.urun_kodu,
            "urun_adi": h.urun_adi,
            "skor": h.toplam_skor,
            "oncelik": h.oncelik_sinifi,
            "telefon_mobil": e.phone_mobile if e else None,
            "telefon_ofis": e.phone_office if e else None,
            "email": e.email_marketing if e else None,
            "yetkili_kisi": e.authorized_person if e else None,
            "yetkili_unvan": e.authorized_title if e else None,
            "rakip_marka": e.current_competitor_brands if e else None,
            "musteri_notu": e.customer_note if e else None,
            "yillik_potansiyel_hacim": float(e.annual_potential_volume) if e and e.annual_potential_volume is not None else None,
            "durum": e.enrichment_status if e else None,
            "last_contact_date": e.last_contact_date.isoformat() if e and e.last_contact_date else None,
            "last_contact_result": e.last_contact_result if e else None,
            "next_visit_date": e.next_visit_date.isoformat() if e and e.next_visit_date else None,
        }
        for (h, f, a, e) in results
    ]

    return {"items": items, "count": len(items)}


@router.get("/today-tasks")
def get_today_tasks(
    only_open: bool = True,
    il: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    today = date.today()

    query = (
        db.query(CrmFirmaZenginlestirme, ResmiFirma, ResmiFirmaAdresi)
        .join(ResmiFirma, ResmiFirma.gln == CrmFirmaZenginlestirme.gln)
        .join(ResmiFirmaAdresi, ResmiFirmaAdresi.gln == CrmFirmaZenginlestirme.gln)
        .filter(CrmFirmaZenginlestirme.next_visit_date == today)
    )

    if il:
        query = query.filter(ResmiFirmaAdresi.il == il)

    if only_open:
        query = query.filter(
            (CrmFirmaZenginlestirme.enrichment_status.is_(None)) |
            (CrmFirmaZenginlestirme.enrichment_status != "KAYBEDILDI")
        )

    results = query.order_by(ResmiFirma.company_name.asc()).limit(limit).all()

    items = [
        {
            "gln": e.gln,
            "firma_adi": f.company_name,
            "il": a.il,
            "ilce": a.ilce,
            "adres": a.adres,
            "telefon_mobil": e.phone_mobile,
            "telefon_ofis": e.phone_office,
            "yetkili_kisi": e.authorized_person,
            "durum": e.enrichment_status,
            "last_contact_date": e.last_contact_date.isoformat() if e.last_contact_date else None,
            "last_contact_result": e.last_contact_result,
            "next_visit_date": e.next_visit_date.isoformat() if e.next_visit_date else None,
            "musteri_notu": e.customer_note,
        }
        for (e, f, a) in results
    ]

    return {"items": items, "count": len(items), "today": today.isoformat()}


@router.post("/activities", response_model=ActivityOut)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    firma = db.get(ResmiFirma, payload.gln)
    if not firma:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")

    row = CrmFirmaAktivitesi(
        gln=payload.gln,
        activity_type=payload.activity_type,
        activity_date=payload.activity_date,
        result=payload.result,
        note=payload.note,
        created_by=payload.created_by,
        next_action_date=payload.next_action_date,
    )
    db.add(row)

    enrich = db.query(CrmFirmaZenginlestirme).filter(
        CrmFirmaZenginlestirme.gln == payload.gln
    ).first()

    if not enrich:
        enrich = CrmFirmaZenginlestirme(gln=payload.gln)
        db.add(enrich)

    enrich.last_contact_date = payload.activity_date.date()
    enrich.last_contact_result = payload.result

    if payload.next_action_date:
        enrich.next_visit_date = payload.next_action_date.date()

    db.commit()
    db.refresh(row)
    return row


@router.get("/activities/today", response_model=list[ActivityOut])
def get_today_activities(
    only_pending_next_action: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    today = date.today()

    query = db.query(CrmFirmaAktivitesi)

    if only_pending_next_action:
        query = query.filter(cast(CrmFirmaAktivitesi.next_action_date, Date) == today)
    else:
        query = query.filter(cast(CrmFirmaAktivitesi.activity_date, Date) == today)

    rows = query.order_by(CrmFirmaAktivitesi.activity_date.desc()).all()
    return rows


@router.get("/activities/overdue", response_model=list[ActivityOut])
def get_overdue_activities(db: Session = Depends(get_db)):
    now = datetime.now()

    rows = (
        db.query(CrmFirmaAktivitesi)
        .filter(
            and_(
                CrmFirmaAktivitesi.next_action_date.is_not(None),
                CrmFirmaAktivitesi.next_action_date < now,
            )
        )
        .order_by(CrmFirmaAktivitesi.next_action_date.asc())
        .all()
    )
    return rows


@router.get("/activities/{gln}", response_model=list[ActivityOut])
def get_activities(gln: str, db: Session = Depends(get_db)):
    firma = db.get(ResmiFirma, gln)
    if not firma:
        raise HTTPException(status_code=404, detail="Firma bulunamadı")

    rows = (
        db.query(CrmFirmaAktivitesi)
        .filter(CrmFirmaAktivitesi.gln == gln)
        .order_by(CrmFirmaAktivitesi.activity_date.desc(), CrmFirmaAktivitesi.id.desc())
        .all()
    )
    return rows


@router.get("/high-priority-uncontacted")
def get_high_priority_uncontacted(
    urun_kodu: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            ResmiFirma.gln,
            ResmiFirma.company_name,
            CrmUrunHedefleme.urun_kodu,
            CrmUrunHedefleme.toplam_skor,
            CrmUrunHedefleme.oncelik_sinifi,
            CrmFirmaZenginlestirme.last_contact_date,
            CrmFirmaZenginlestirme.enrichment_status,
        )
        .join(CrmUrunHedefleme, CrmUrunHedefleme.gln == ResmiFirma.gln)
        .outerjoin(CrmFirmaZenginlestirme, CrmFirmaZenginlestirme.gln == ResmiFirma.gln)
        .filter(CrmUrunHedefleme.oncelik_sinifi.in_(["A", "B"]))
        .filter(CrmFirmaZenginlestirme.last_contact_date.is_(None))
    )

    if urun_kodu:
        query = query.filter(CrmUrunHedefleme.urun_kodu == urun_kodu)

    rows = (
        query.order_by(
            CrmUrunHedefleme.oncelik_sinifi.asc(),
            CrmUrunHedefleme.toplam_skor.desc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "gln": r.gln,
            "firma_adi": r.company_name,
            "urun_kodu": r.urun_kodu,
            "toplam_skor": r.toplam_skor,
            "oncelik": r.oncelik_sinifi,
            "last_contact_date": r.last_contact_date.isoformat() if r.last_contact_date else None,
            "durum": r.enrichment_status,
        }
        for r in rows
    ]