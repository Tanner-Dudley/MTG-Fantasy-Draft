from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "change-me-to-a-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    database_url: str = "sqlite:///./dev.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
