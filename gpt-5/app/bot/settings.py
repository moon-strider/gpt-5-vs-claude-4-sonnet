import os
from pydantic import BaseModel, ValidationError


class Settings(BaseModel):
    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str
    APP_TZ: str = "UTC"
    LOG_LEVEL: str = "INFO"
    MAX_PROMPT_TOKENS: int = 24000


def load_settings() -> Settings:
    data = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "APP_TZ": os.getenv("APP_TZ", "UTC"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "MAX_PROMPT_TOKENS": int(os.getenv("MAX_PROMPT_TOKENS", "24000")),
    }
    settings = Settings(**data)
    if settings.APP_TZ != "UTC":
        raise ValidationError.from_exception_data("APP_TZ", [{"type": "value_error", "loc": ("APP_TZ",), "msg": "APP_TZ must be UTC", "input": settings.APP_TZ}])
    return settings

