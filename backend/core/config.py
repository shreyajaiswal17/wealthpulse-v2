from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str = "wealthpulse-local"
    GROQ_API_KEY: str
    GEMINI_API_KEY: str
    FINNHUB_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
