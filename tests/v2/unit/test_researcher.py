from http import HTTPStatus


def test_read_researcher(client):
    response = client.get('/v2/researcher')
    assert response.status_code == HTTPStatus.OK
    print(response.json())
