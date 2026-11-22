import re
from functools import lru_cache
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.model import Researcher
from simcc.core.settings import get_settings

CNPQ_IMAGE_URL = (
    'http://servicosweb.cnpq.br/wspessoa/servletrecuperafoto?tipo=1&id='
)

DEFAULT_AVATAR_PATH = (
    Path(__file__).resolve().parent.parent
    / 'static'
    / 'images'
    / 'default_avatar.png'
)

LATTES_10_PATTERN = re.compile(r'^[A-Za-z0-9]{10}$')

RESEARCHER_IMAGE_DIR = Path('storage/image_researcher')


async def download_researcher_image(
    researcher_id: str, session: AsyncSession | None = None
):
    path = RESEARCHER_IMAGE_DIR / f'{researcher_id}.jpg'

    if path.exists() or not session:
        return

    # Busca o lattes_10_id do pesquisador
    query = select(Researcher.lattes_10_id).where(
        Researcher.id == researcher_id
    )
    result = await session.execute(query)
    lattes_10_id = result.scalar_one_or_none()

    if not lattes_10_id or not LATTES_10_PATTERN.match(lattes_10_id):
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    url = f'{CNPQ_IMAGE_URL}{lattes_10_id}'

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

            if response.status_code == 200:
                # CNPq pode retornar 200 com conteúdo vazio ou erro HTML dependendo do caso
                if (
                    len(response.content) > 0
                    and b'html' not in response.content[:100].lower()
                ):
                    path.write_bytes(response.content)
    except Exception:
        pass


INSTITUTIONS_STORAGE_DIR = Path('storage/institutions')
INSTITUTIONS_PICTURE_DIR = INSTITUTIONS_STORAGE_DIR / 'picture'
INSTITUTIONS_COVERS_DIR = INSTITUTIONS_STORAGE_DIR / 'covers'


def get_institution_logo_path(acronym: str | None) -> Path | None:
    if not acronym:
        return None
    acronym_clean = acronym.strip().upper()
    for ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg']:
        p = INSTITUTIONS_PICTURE_DIR / f'{acronym_clean}{ext}'
        if p.exists():
            return p
    return None


def get_institution_cover_path(acronym: str | None) -> Path | None:
    if not acronym:
        return None
    acronym_clean = acronym.strip().upper()
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        p = INSTITUTIONS_COVERS_DIR / f'{acronym_clean}{ext}'
        if p.exists():
            return p
    return None


def _build_institution_storage_url(
    path: Path | None, subdir: str, base_url: str | None = None
) -> str | None:
    if not path:
        return None
    resolved_base = (
        base_url.strip().rstrip('/')
        if base_url is not None
        else get_settings().storage_base_url
    )
    rel_path = f'/storage/institutions/{subdir}/{path.name}'
    return f'{resolved_base}{rel_path}' if resolved_base else rel_path


# Cacheado por processo: arquivos novos exigem reinício do servidor.
@lru_cache(maxsize=256)
def get_institution_logo_url(
    acronym: str | None, base_url: str | None = None
) -> str | None:
    return _build_institution_storage_url(
        get_institution_logo_path(acronym), 'picture', base_url
    )


@lru_cache(maxsize=256)
def get_institution_cover_url(
    acronym: str | None, base_url: str | None = None
) -> str | None:
    return _build_institution_storage_url(
        get_institution_cover_path(acronym), 'covers', base_url
    )
