from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/songbuilder"
    admin_email: str = ""
    admin_password: str = ""
    session_secret: str = ""
    cookie_secure: bool = False
    ai_api_key: str = ""
    ai_base_url: str = "https://polza.ai/api/v1"
    ai_model: str = "claude-haiku-5.5"
    ai_timeout_seconds: float = 60.0


settings = Settings()
