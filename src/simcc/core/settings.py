from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings, extra='ignore'):
    DATABASE_URL: str
    INTERNAL_API_KEY: Optional[str] = None

    URL: str = 'http://localhost:0000/'
    STORAGE_URL: Optional[str] = None
    ROOT_PATH: str = Field(
        default='',
        validation_alias=AliasChoices(
            'ROOT_PATH', 'API_ROOT_PATH', 'FASTAPI_ROOT_PATH'
        ),
    )

    # Configurações de Cache (Redis)
    REDIS_URL: str = 'redis://localhost:6379/0'
    REDIS_ENABLED: bool = True

    # Configurações do Google Analytics 4 (GA4)
    GA4_PROPERTY_ID: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'GA4_PROPERTY_ID', 'VITE_GA4_PROPERTY_ID'
        ),
    )
    GA4_SITE_URL: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('GA4_SITE_URL', 'VITE_URL_SITE'),
    )

    @field_validator('ROOT_PATH', mode='before')
    @classmethod
    def assemble_root_path(cls, v: Optional[str]) -> str:
        if v:
            path = v.strip().rstrip('/')
            if path and not path.startswith('/'):
                path = f'/{path}'
            return path
        return ''

    @model_validator(mode='after')
    def set_default_root_path(self) -> 'Settings':
        if not self.ROOT_PATH and self.URL:
            path = urlparse(self.URL).path.rstrip('/')
            if path:
                self.ROOT_PATH = path
        return self

    @property
    def storage_base_url(self) -> str:
        """Base pública usada para compor URLs de arquivos em storage."""
        base = self.STORAGE_URL or self.URL
        return base.strip().rstrip('/')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


@lru_cache
def get_settings() -> Settings:
    return Settings()
