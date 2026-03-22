from sqlalchemy import Column, Integer, Text, TIMESTAMP
from app.core.database import Base
from datetime import datetime

class BkuTavsiye(Base):
    __tablename__ = "bku_tavsiyeler"

    id = Column(Integer, primary_key=True, index=True)
    bitki_adi = Column(Text)
    zararli_organizma = Column(Text)
    aktif_madde = Column(Text)
    urun_adi = Column(Text)
    tavsiye_durumu = Column(Text)
    grup_adi = Column(Text)
    doz = Column(Text)
    hasat_arasi_sure = Column(Text)
    kaynak = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)