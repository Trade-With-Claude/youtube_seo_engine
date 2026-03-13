from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./seo_engine.db"
    youtube_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
