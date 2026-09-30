import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from simcc.v1.routers import logs
from simcc.v1.routers.logs import router as logs_router, broadcast_log_to_websockets


def test_websocket_stream_authentication(monkeypatch):
    app = FastAPI()
    app.include_router(logs_router)

    # Configura token de teste
    test_token = "secret-token-12345"
    monkeypatch.setattr(logs, "FALLBACK_TOKEN", test_token)
    monkeypatch.setattr(logs.settings, "LOG_STREAM_TOKEN", test_token)

    client = TestClient(app)

    # 1. Teste com token inválido -> fecha com 4003
    with pytest.raises(Exception):
        with client.websocket_connect("/logs/stream?token=wrong-token"):
            pass

    # 2. Teste sem token -> fecha com 4003
    with pytest.raises(Exception):
        with client.websocket_connect("/logs/stream"):
            pass

    # 3. Teste com token válido e recebimento de broadcast
    # Note: no código atual do router, ele procura settings.LOG_WEBSOCKET_TOKEN or FALLBACK_TOKEN
    # Com FALLBACK_TOKEN configurado, deve conectar e receber mensagem
    with client.websocket_connect(f"/logs/stream?token={test_token}") as ws:
        log_payload = {
            "level": "info",
            "event": "websocket.test_broadcast",
            "message": "Mensagem enviada para o websocket",
        }
        broadcast_log_to_websockets(log_payload)

        data = ws.receive_text()
        parsed = json.loads(data)
        assert parsed["event"] == "websocket.test_broadcast"
        assert parsed["message"] == "Mensagem enviada para o websocket"
