from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    gln: str
    urun_kodu: str
    konum_skoru: int = 0
    kategori_skoru: int = 0
    adres_tipi_skoru: int = 0
    potansiyel_skoru: int = 0
    toplam_skor: int = 0
    oncelik_sinifi: str = "D"
    score_explain: dict = {}
