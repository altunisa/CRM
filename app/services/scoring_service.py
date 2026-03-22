from datetime import datetime
from sqlalchemy.orm import Session

from app.models.resmi import ResmiFirma, ResmiFirmaAdresi
from app.models.crm import CrmUrunHedefleme, CrmUrunProfili


class ScoringService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""

        text = value.strip().upper()

        replacements = {
            "İ": "I",
            "I": "I",
            "Ş": "S",
            "Ğ": "G",
            "Ü": "U",
            "Ö": "O",
            "Ç": "C",
            "Â": "A",
            "Ê": "E",
            "Î": "I",
            "Û": "U",
        }

        for src, dst in replacements.items():
            text = text.replace(src, dst)

        return text
    def _score_location(self, firma_adres, urun_profili):
        il = self._normalize_text(firma_adres.il)
        ilce = self._normalize_text(firma_adres.ilce)

        il_map = urun_profili.il_skor_map or {}
        ilce_map = urun_profili.ilce_skor_map or {}

        il_skor = 0
        ilce_skor = 0

        for key, val in il_map.items():
            if self._normalize_text(key) == il:
                il_skor = int(val or 0)
                break

        for key, val in ilce_map.items():
            if self._normalize_text(key) == ilce:
                ilce_skor = int(val or 0)
                break

        return il_skor + ilce_skor, {
            "il": il,
            "ilce": ilce,
            "il_skor": il_skor,
            "ilce_skor": ilce_skor,
        }

    def _score_company_type(self, firma, urun_profili):
        company_type = self._normalize_text(firma.company_type)
        kategori_map = urun_profili.kategori_skor_map or {}

        skor = 0
        for key, val in kategori_map.items():
            if self._normalize_text(key) == company_type:
                skor = int(val or 0)
                break

        return skor, {
            "company_type": company_type,
            "company_type_skor": skor,
        }

    def _score_address_type(self, firma_adres, urun_profili):
        address_type = self._normalize_text(firma_adres.address_type)
        adres_map = urun_profili.adres_tipi_skor_map or {}

        skor = 0
        for key, val in adres_map.items():
            if self._normalize_text(key) == address_type:
                skor = int(val or 0)
                break

        return skor, {
            "address_type": address_type,
            "address_type_skor": skor,
        }

    def _score_potential(self, gln: str):
        # Şimdilik sabit / placeholder.
        # Sonra crm_firma_zenginlestirme.annual_potential_volume alanına göre geliştirilebilir.
        return 0, {
            "potential_skor": 0
        }

    @staticmethod
    def _priority_class(total_score: int) -> str:
        if total_score >= 14:
            return "A"
        if total_score >= 10:
            return "B"
        if total_score >= 6:
            return "C"
        return "D"

    def recalculate(self):
        firma_listesi = self.db.query(ResmiFirma).all()
        urun_profilleri = self.db.query(CrmUrunProfili).filter(CrmUrunProfili.aktif.is_(True)).all()

        toplam_kayit = 0

        for firma in firma_listesi:
            firma_adres = (
                self.db.query(ResmiFirmaAdresi)
                .filter(ResmiFirmaAdresi.gln == firma.gln)
                .first()
            )

            if not firma_adres:
                continue

            for profil in urun_profilleri:
                location_score, location_explain = self._score_location(firma_adres, profil)
                company_score, company_explain = self._score_company_type(firma, profil)
                address_score, address_explain = self._score_address_type(firma_adres, profil)
                potential_score, potential_explain = self._score_potential(firma.gln)

                total_score = location_score + company_score + address_score + potential_score
                priority = self._priority_class(total_score)

                existing = (
                    self.db.query(CrmUrunHedefleme)
                    .filter(
                        CrmUrunHedefleme.gln == firma.gln,
                        CrmUrunHedefleme.urun_kodu == profil.urun_kodu
                    )
                    .first()
                )

                if not existing:
                    existing = CrmUrunHedefleme(
                        gln=firma.gln,
                        urun_kodu=profil.urun_kodu
                    )
                    self.db.add(existing)

                existing.urun_adi = profil.urun_adi
                existing.hedef_il = firma_adres.il
                existing.hedef_ilce = firma_adres.ilce
                existing.konum_skoru = location_score
                existing.kategori_skoru = company_score
                existing.adres_tipi_skoru = address_score
                existing.potansiyel_skoru = potential_score
                existing.toplam_skor = total_score
                existing.oncelik_sinifi = priority
                existing.score_explain = {
                    **location_explain,
                    **company_explain,
                    **address_explain,
                    **potential_explain,
                }
                existing.calculated_at = datetime.utcnow()

                toplam_kayit += 1

        self.db.commit()

        return {
            "message": "Skor hesaplama tamamlandı",
            "processed_records": toplam_kayit,
            "active_product_profiles": len(urun_profilleri),
        }
