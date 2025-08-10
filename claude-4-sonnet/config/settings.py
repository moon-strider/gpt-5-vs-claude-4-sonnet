import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    openai_api_key: str
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False
    )
    
    @field_validator('telegram_bot_token')
    @classmethod
    def validate_telegram_token(cls, v):
        if not v or v == 'your_telegram_bot_token_here':
            raise ValueError('TELEGRAM_BOT_TOKEN must be provided')
        return v
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_key(cls, v):
        if not v or v == 'your_openai_api_key_here':
            raise ValueError('OPENAI_API_KEY must be provided')
        return v


def get_settings() -> Settings:
    return Settings()