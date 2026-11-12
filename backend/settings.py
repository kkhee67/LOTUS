from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', env_file_encoding='utf-8', extra='ignore')
    cors_origins: str = 'http://localhost:5173'
    database_url: str = 'sqlite:///runtime/lotus.db'
    data_mode: str = Field(default='demo', pattern='^(demo|real)$')

    @field_validator('cors_origins')
    @classmethod
    def origins(cls, value):
        from urllib.parse import urlsplit
        for origin in value.split(','):
            parsed = urlsplit(origin.strip())
            if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
                raise ValueError('CORS origins must be server origins only')
        return value

    @property
    def allowed_origins(self):
        return [x.strip() for x in self.cors_origins.split(',')]
