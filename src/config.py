"""Centralized config/env loading for pr-sentinal."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    github_token: str
    groq_api_key: str
    openai_api_key: str
    database_url: str


def get_settings() -> Settings:
    missing = [
        name
        for name in ("GITHUB_TOKEN", "GROQ_API_KEY", "DATABASE_URL")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in."
        )

    return Settings(
        github_token=os.environ["GITHUB_TOKEN"],
        groq_api_key=os.environ["GROQ_API_KEY"],
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        database_url=os.environ["DATABASE_URL"],
    )
