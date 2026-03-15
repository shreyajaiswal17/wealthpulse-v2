from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str = ""
    REDIS_URL: str
    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str = "wealthpulse-local"
    GROQ_API_KEY: str
    GEMINI_API_KEY: str
    FINNHUB_API_KEY: str

    @model_validator(mode="after")
    def derive_sync_url(self):
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = self.DATABASE_URL.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
        return self

    class Config:
        env_file = ".env"


settings = Settings()
