-- Faz 1: Firma sınıflandırma alanları
ALTER TABLE IF EXISTS crm_firma_zenginlestirme
    ADD COLUMN IF NOT EXISTS ruhsat_sahibi BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS uretici BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ithalatci BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS bayi BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS toptanci BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS distributor BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS karma_firma BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS firma_tipi_ana VARCHAR(64),
    ADD COLUMN IF NOT EXISTS hedef_iliski_tipi VARCHAR(64),
    ADD COLUMN IF NOT EXISTS firma_segment VARCHAR(64),
    ADD COLUMN IF NOT EXISTS stratejik_skor DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kanal_skor DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS operasyon_skor DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS siniflandirma_notu TEXT,
    ADD COLUMN IF NOT EXISTS siniflandirma_kaynagi VARCHAR(64),
    ADD COLUMN IF NOT EXISTS siniflandirma_guncelleme_tarihi TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_crm_fz_firma_tipi_ana ON crm_firma_zenginlestirme (firma_tipi_ana);
CREATE INDEX IF NOT EXISTS ix_crm_fz_hedef_iliski_tipi ON crm_firma_zenginlestirme (hedef_iliski_tipi);
CREATE INDEX IF NOT EXISTS ix_crm_fz_firma_segment ON crm_firma_zenginlestirme (firma_segment);

-- Faz 2-3: BKU karar motoru performansı
CREATE INDEX IF NOT EXISTS ix_bku_ruhsatlar_ruhsat_sahibi_upper
    ON bku_ruhsatlar (upper(ruhsat_sahibi));

CREATE INDEX IF NOT EXISTS ix_bku_tavsiyeler_bitki_il_urun
    ON bku_tavsiyeler (bitki, il, urun_adi);
