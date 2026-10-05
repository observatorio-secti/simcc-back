from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings, extra='ignore'):
    ROOT_PATH: str = ''

    URL: Optional[str] = 'http://localhost:8000'
    ADMIN_URL: str = 'http://localhost:9090'

    DATABASE_URL: str
    ADMIN_DATABASE_URL: str

    PROXY_URL: str = 'http://localhost:8080'
    ALTERNATIVE_CNPQ_SERVICE: bool = False
    FIREBASE_COLLECTION: str = 'termos_busca'

    XML_PATH: str = 'storage/xml'
    CURRENT_XML_PATH: str = 'storage/xml/current'
    ZIP_XML_PATH: str = 'storage/xml/current'

    OPENAI_API_KEY: str = None

    # Configurações de Alerta de Auditoria e E-mail (ETL Data Quality)
    SMTP_HOST: Optional[str] = 'smtp.gmail.com'
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = ''
    SMTP_PASSWORD: Optional[str] = ''
    SMTP_FROM: Optional[str] = ''
    ALERT_EMAILS: Optional[str] = 'eric.queiroz@aln.senaicimatec.edu.br,ejorge@uneb.br'
    ALERT_ON_SUCCESS: bool = False

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
