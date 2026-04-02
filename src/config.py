"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Sherlock platform configuration.

    Values are loaded from environment variables or a .env file.
    """

    # Database
    database_url: str = "sqlite:///data/sherlock.db"

    # API-Football (api-sports.io)
    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # BallDontLie API
    balldontlie_api_key: str = ""
    balldontlie_base_url: str = "https://api.balldontlie.io/v1"

    # TheSportsDB
    thesportsdb_base_url: str = "https://www.thesportsdb.com/api/v1/json/3"

    # OpenRouter (Nemotron)
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
