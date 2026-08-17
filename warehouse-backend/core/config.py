from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Warehouse Management System"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "warehouse_management"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5199,http://127.0.0.1:5199"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    bootstrap_owner_email: str = "admin@whitfieldfulfillment.com"
    bootstrap_owner_password: str = ""
    bootstrap_owner_first_name: str = "Warehouse"
    bootstrap_owner_last_name: str = "Owner"
    bootstrap_owner_mobile: str = "0000000000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        """Parse the comma-delimited CORS origin configuration."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load and cache environment-backed application settings."""
    return Settings()


settings = get_settings()
