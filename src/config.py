from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET_KEY: str
    APP_BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bhoomisatya"
    REDIS_URL: str = "redis://localhost:6379/0"

    ANTHROPIC_API_KEY: str

    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_APP_SECRET: str

    BHASHINI_API_KEY: str
    BHASHINI_USER_ID: str
    BHASHINI_PIPELINE_URL: str = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    GOOGLE_MAPS_API_KEY: str

    PROXY_URL: str | None = None
    CAPTCHA_SOLVER_API_KEY: str | None = None
    PLAYWRIGHT_HEADLESS: bool = True

    SENTRY_DSN: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
