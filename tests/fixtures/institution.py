import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core import utils
from tests.factories.institution import InstitutionFactory


@pytest_asyncio.fixture
def institution_factory(session: AsyncSession):
    async def _create_institution(**kwargs):
        institution = InstitutionFactory(**kwargs)
        session.add(institution)
        await session.commit()
        return institution

    return _create_institution


@pytest.fixture
def institution_storage(tmp_path, monkeypatch):
    """Isola o diretório de logos/capas e cria arquivos para uma sigla."""
    picture_dir = tmp_path / 'picture'
    covers_dir = tmp_path / 'covers'
    picture_dir.mkdir()
    covers_dir.mkdir()
    monkeypatch.setattr(utils, 'INSTITUTIONS_PICTURE_DIR', picture_dir)
    monkeypatch.setattr(utils, 'INSTITUTIONS_COVERS_DIR', covers_dir)
    utils.get_institution_logo_url.cache_clear()
    utils.get_institution_cover_url.cache_clear()

    def _add_images(acronym: str):
        (picture_dir / f'{acronym}.png').touch()
        (covers_dir / f'{acronym}.jpg').touch()

    yield _add_images

    utils.get_institution_logo_url.cache_clear()
    utils.get_institution_cover_url.cache_clear()
