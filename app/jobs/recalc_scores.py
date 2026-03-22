from app.services.scoring_service import ScoringService


if __name__ == "__main__":
    service = ScoringService()
    print(service.calculate(gln="8690000000001", urun_kodu="URUN-001", konum_skoru=8, kategori_skoru=3, adres_tipi_skoru=2, potansiyel_skoru=4))
