from sqlalchemy import text
from sqlalchemy.orm import Session


class GeoService:
    def __init__(self, db: Session):
        self.db = db

    def nearby_high_score(self, lat: float, lon: float, radius_km: float = 25):
        sql = text(
            """
            SELECT
                f.gln,
                f.company_name,
                a.il,
                a.ilce,
                a.adres,
                a.latitude,
                a.longitude,
                h.toplam_skor,
                h.oncelik_sinifi
            FROM resmi_firmalar f
            JOIN resmi_firma_adresleri a ON a.gln = f.gln
            JOIN crm_urun_hedefleme h ON h.gln = f.gln
            WHERE h.oncelik_sinifi IN ('A','B')
              AND a.latitude IS NOT NULL
              AND a.longitude IS NOT NULL
            """
        )
        rows = self.db.execute(sql).mappings().all()
        # İlk sürümde kaba filtre döner; PostGIS eklenince gerçek mesafe hesabı yapılır.
        return {
            "center": {"lat": lat, "lon": lon},
            "radius_km": radius_km,
            "count": len(rows),
            "items": [dict(r) for r in rows],
        }
