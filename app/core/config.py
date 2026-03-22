
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Akıllı CRM & Pazarlama ERP"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str
    MINISTRY_USE_MOCK: bool = True
    MINISTRY_BASE_URL: str = "https://bkst.tarbil.gov.tr/Service"
    MINISTRY_TOKEN_URL: str = "https://bkst.tarbil.gov.tr/Service/Token"
    MINISTRY_USERNAME: str = "39277285148"
    MINISTRY_PASSWORD: str = "392.!+148"
    BKST_GLN: str = "8680742318513"
    BKST_KEY: str = "3b67531e-b4a1-492c-aca5-0d47fe7c34be"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()