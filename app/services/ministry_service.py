from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resmi import ResmiFirma, ResmiFirmaAdresi
from app.models.crm import CrmFirmaZenginlestirme
from app.services.token_util import get_token

def parse_company_address(company_address: str) -> dict:
    """
    BKST CompanyAddress alanını kaba şekilde ayrıştırır.
    Beklenen örnek:
    BURSA/OSMANGAZİ YUNUSELİ MAHALLESİ ÇAMLIK CADDESİ A BLOK NO:38 /A D
    """
    result = {
        "il": None,
        "ilce": None,
        "mahalle": None,
        "adres_detay": company_address.strip() if company_address else None,
    }

    if not company_address:
        return result

    text = " ".join(company_address.strip().split())

    # İl / ilçe ayır
    if "/" in text:
        il_part, rest = text.split("/", 1)
        result["il"] = il_part.strip() or None
    else:
        rest = text

    rest = rest.strip()

    # İlk kelimeyi ilçe kabul et
    if rest:
        parts = rest.split()
        if parts:
            result["ilce"] = parts[0].strip() or None

    # Mahalleyi bul
    mahalle_markers = [" MAHALLESİ", " MAH.", " MAH"]
    upper_rest = rest.upper()

    mahalle_end = -1
    marker_used = None
    for marker in mahalle_markers:
        idx = upper_rest.find(marker)
        if idx != -1:
            mahalle_end = idx + len(marker)
            marker_used = marker
            break

    if mahalle_end != -1:
        # ilçe ilk kelime, mahalle ilçe sonrasından marker sonuna kadar
        first_space = rest.find(" ")
        if first_space != -1:
            mahalle_text = rest[first_space + 1:mahalle_end].strip()
            result["mahalle"] = mahalle_text or None

    return result
def normalize_company_type(value: str | None) -> str | None:
    if not value:
        return None

    text = value.strip().upper()

    replacements = {
        "İ": "I",
        "Ş": "S",
        "Ğ": "G",
        "Ü": "U",
        "Ö": "O",
        "Ç": "C",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    mapping = {
        "BAYI": "BAYI",
        "FIRMA": "FIRMA",
        "TOPTANCI": "TOPTANCI",
    }

    return mapping.get(text, text)


def normalize_address_type(value: str | None) -> str | None:
    if not value:
        return None

    text = value.strip().upper()

    replacements = {
        "İ": "I",
        "Ş": "S",
        "Ğ": "G",
        "Ü": "U",
        "Ö": "O",
        "Ç": "C",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    mapping = {
        "DEPO": "DEPO",
        "FAALIYET": "FAALIYET",
        "FAALIYET": "FAALIYET",
    }

    return mapping.get(text, text)
class MinistryService:
    def __init__(self, db: Session):
        self.db = db

    def _upsert_firm_records(self, items: list[dict], default_tax_no: str | None = None):
        synced = 0
        queued_for_enrichment = 0

        # 1) Aynı listedeki mükerrer GLN kayıtlarını temizle
        unique_items: dict[str, dict] = {}
        for item in items:
            gln = str(item.get("Gln_Pn") or item.get("GLN") or "").strip()
            if not gln:
                continue
            unique_items[gln] = item

        # 2) DB'de mevcut olan GLN'leri topluca çek
        gln_list = list(unique_items.keys())

        existing_firms = {
            x.gln: x
            for x in self.db.query(ResmiFirma).filter(ResmiFirma.gln.in_(gln_list)).all()
        }

        existing_addresses = {
            x.gln: x
            for x in self.db.query(ResmiFirmaAdresi).filter(ResmiFirmaAdresi.gln.in_(gln_list)).all()
        }

        existing_enrich = {
            x.gln: x
            for x in self.db.query(CrmFirmaZenginlestirme).filter(CrmFirmaZenginlestirme.gln.in_(gln_list)).all()
        }

        for gln, item in unique_items.items():
            firma = existing_firms.get(gln)
            if not firma:
                firma = ResmiFirma(gln=gln)
                self.db.add(firma)
                existing_firms[gln] = firma

            firma.company_name = item.get("CompanyName")
            firma.company_title = item.get("CompanyTitle")
            firma.company_type = normalize_company_type(
                item.get("COMPANYTYPE") or item.get("CompanyType")
            )
            firma.tax_no = item.get("TaxNo") or default_tax_no
            firma.is_active = True
            firma.source_system = "BKST"
            firma.source_last_sync_at = datetime.utcnow()
            firma.raw_json = item

            adres = existing_addresses.get(gln)
            if not adres:
                adres = ResmiFirmaAdresi(gln=gln)
                self.db.add(adres)
                existing_addresses[gln] = adres

            company_address = (item.get("CompanyAddress") or "").strip()
            parsed_address = parse_company_address(company_address)

            adres.address_type = normalize_address_type(
                item.get("ADDRESSTYPE") or item.get("AddressType")
            )
            adres.il = parsed_address["il"]
            adres.ilce = parsed_address["ilce"]
            adres.mahalle = parsed_address["mahalle"]
            adres.posta_kodu = None
            adres.adres = parsed_address["adres_detay"]
            adres.latitude = None
            adres.longitude = None
            adres.source_last_sync_at = datetime.utcnow()
            adres.raw_json = item

            enrich = existing_enrich.get(gln)
            if not enrich:
                enrich = CrmFirmaZenginlestirme(
                    gln=gln,
                    enrichment_status="waiting",
                )
                self.db.add(enrich)
                existing_enrich[gln] = enrich
                queued_for_enrichment += 1

            synced += 1

        self.db.commit()

        return {
            "synced": synced,
            "queued_for_enrichment": queued_for_enrichment,
        }
    async def sync_dealers(self):
        items = await self.fetch_dealers()
        result = self._upsert_firm_records(items)
        return {
            "message": "Bayi listesi senkronizasyonu tamamlandı",
            **result,
            "source": "BKST",
            "list_type": "dealer",
        }

    async def sync_wholesalers(self):
        items = await self.fetch_wholesalers()
        result = self._upsert_firm_records(items)
        return {
            "message": "Toptancı listesi senkronizasyonu tamamlandı",
            **result,
            "source": "BKST",
            "list_type": "wholesaler",
        }

    async def sync_licencees(self):
        items = await self.fetch_licencees()
        result = self._upsert_firm_records(items)
        return {
            "message": "Ruhsatlı üretici listesi senkronizasyonu tamamlandı",
            **result,
            "source": "BKST",
            "list_type": "licencee",
        }
    async def fetch_firms_from_ministry(self, id_or_tax_no: str):
        if settings.MINISTRY_USE_MOCK:
            return [
                {
                    "Gln_Pn": "8690000000001",
                    "CompanyName": "Demo Tarım",
                    "CompanyTitle": "Demo Tarım Ltd. Şti.",
                    "CompanyType": "Bayi",
                    "TaxNo": id_or_tax_no,
                    "AddressType": "Faaliyet",
                    "Il": "Bursa",
                    "Ilce": "Nilüfer",
                    "Mahalle": "23 Nisan",
                    "PostaKodu": "16140",
                    "Address": "İzmir Yolu Cd. No:10 Nilüfer/Bursa",
                    "Latitude": 40.2200,
                    "Longitude": 28.9500,
                }
            ]

        token = await get_token()

        url = f"{settings.MINISTRY_BASE_URL}/main/getGlnWithIdTaxNo"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        params = {
            "Key": settings.BKST_KEY,
            "Gln": settings.BKST_GLN,
            "IdTaxNo": id_or_tax_no,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            print("BKST STATUS:", response.status_code)
            print("BKST TEXT:", response.text[:3000])
            response.raise_for_status()
            data = response.json()
            print("BKST JSON:", data)

        if isinstance(data, dict) and "Data" in data:
            return data["Data"] or []

        if isinstance(data, list):
            return data

        return []

    async def sync_firms(self, id_or_tax_no: str):
        items = await self.fetch_firms_from_ministry(id_or_tax_no=id_or_tax_no)
        result = self._upsert_firm_records(items, default_tax_no=id_or_tax_no)

        return {
            "message": "Firma senkronizasyonu tamamlandı",
            **result,
            "source": "MOCK" if settings.MINISTRY_USE_MOCK else "BKST",
        }

        for item in items:
            gln = str(item.get("Gln_Pn") or item.get("GLN") or "").strip()
            if not gln:
                continue

            firma = self.db.get(ResmiFirma, gln)
            if not firma:
                firma = ResmiFirma(gln=gln)
                self.db.add(firma)

            firma.company_name = item.get("CompanyName")
            firma.company_title = item.get("CompanyTitle")
            firma.company_type = item.get("COMPANYTYPE") or item.get("CompanyType")
            firma.tax_no = item.get("TaxNo") or id_or_tax_no
            firma.is_active = True
            firma.source_system = "BKST"
            firma.source_last_sync_at = datetime.utcnow()
            firma.raw_json = item

            adres = (
                self.db.query(ResmiFirmaAdresi)
                .filter(ResmiFirmaAdresi.gln == gln)
                .first()
            )
            if not adres:
                adres = ResmiFirmaAdresi(gln=gln)
                self.db.add(adres)

            company_address = (item.get("CompanyAddress") or "").strip()
            parsed_address = parse_company_address(company_address)

            adres.address_type = item.get("ADDRESSTYPE") or item.get("AddressType")
            adres.il = parsed_address["il"]
            adres.ilce = parsed_address["ilce"]
            adres.mahalle = parsed_address["mahalle"]
            adres.posta_kodu = None
            adres.adres = parsed_address["adres_detay"]
            adres.latitude = None
            adres.longitude = None
            adres.source_last_sync_at = datetime.utcnow()
            adres.raw_json = item

            enrich = self.db.get(CrmFirmaZenginlestirme, gln)
            if not enrich:
                enrich = CrmFirmaZenginlestirme(
                    gln=gln,
                    enrichment_status="waiting",
                )
                self.db.add(enrich)
                queued_for_enrichment += 1

            synced += 1

        self.db.commit()

        return {
            "message": "Firma senkronizasyonu tamamlandı",
            "synced": synced,
            "queued_for_enrichment": queued_for_enrichment,
            "source": "MOCK" if settings.MINISTRY_USE_MOCK else "BKST",
        }
    async def _fetch_list_endpoint(self, endpoint_name: str):
        token = await get_token()

        url = f"{settings.MINISTRY_BASE_URL}/main/{endpoint_name}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and "Data" in data:
            return data["Data"] or []

        if isinstance(data, list):
            return data

        return []

    async def fetch_dealers(self):
        return await self._fetch_list_endpoint("getDealerList")

    async def fetch_wholesalers(self):
        return await self._fetch_list_endpoint("getWholesalerList")

    async def fetch_licencees(self):
        return await self._fetch_list_endpoint("getLicenceeFirmList")