from http import HTTPStatus
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from simcc import app
from simcc.core.db.database import get_async_session
from simcc.v1.services import researcher_service


@pytest.fixture
def test_client():
    mock_session = AsyncMock()

    async def get_session_override():
        yield mock_session

    app.dependency_overrides[get_async_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.unit
def test_get_institution_image_by_acronym(test_client):
    response = test_client.get('/institution/image?acronym=UFBA')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'image/png'
    assert len(response.content) > 0


@pytest.mark.unit
def test_get_institution_image_by_path_param(test_client):
    response = test_client.get('/institution/image/UFBA')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'image/png'
    assert len(response.content) > 0


@pytest.mark.unit
def test_get_institution_cover_by_acronym(test_client):
    response = test_client.get('/institution/cover?acronym=UFBA')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'image/jpeg'
    assert len(response.content) > 0


@pytest.mark.unit
def test_get_institution_cover_by_path_param(test_client):
    response = test_client.get('/institution/cover/UFOB')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'image/jpeg'
    assert len(response.content) > 0


@pytest.mark.unit
def test_get_institution_image_not_found(test_client):
    response = test_client.get('/institution/image/INEXISTENTE')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.unit
def test_get_institution_cover_not_found(test_client):
    response = test_client.get('/institution/cover/INEXISTENTE')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.unit
def test_get_institution_image_missing_params(test_client):
    response = test_client.get('/institution/image')
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.unit
def test_get_institution_list_endpoint(test_client, monkeypatch):
    inst_id = uuid4()
    mock_data = [
        {
            'id': inst_id,
            'name': 'Universidade Federal da Bahia',
            'acronym': 'UFBA',
            'count_r': 100,
            'count_gp': 10,
            'count_gpr': 20,
            'count_gps': 30,
            'count_d': 0,
            'count_t': 0,
            'count_rg': 0,
            'count_foment': 0,
            'researchers': [],
            'image': '/storage/institutions/picture/UFBA.png',
            'cover': '/storage/institutions/covers/UFBA.jpg',
        }
    ]

    async def mock_list(session):
        return mock_data

    monkeypatch.setattr(researcher_service, 'list_institutions', mock_list)

    response = test_client.get('/institution')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]['acronym'] == 'UFBA'
    assert data[0]['image'] == '/storage/institutions/picture/UFBA.png'
    assert data[0]['cover'] == '/storage/institutions/covers/UFBA.jpg'


@pytest.mark.unit
def test_static_storage_institutions_mount(test_client):
    # Valida se o mount de arquivos estáticos /storage/institutions funciona diretamente
    resp_logo = test_client.get('/storage/institutions/picture/UFBA.png')
    assert resp_logo.status_code == HTTPStatus.OK
    assert len(resp_logo.content) > 0

    resp_cover = test_client.get('/storage/institutions/covers/UFBA.jpg')
    assert resp_cover.status_code == HTTPStatus.OK
    assert len(resp_cover.content) > 0
