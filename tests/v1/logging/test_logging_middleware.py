import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from simcc.core.logging.handlers import LOG_DESTINATIONS
from simcc.core.logging.middleware import LoggingMiddleware


def test_logging_middleware_flow():
    test_app = FastAPI()
    test_app.add_middleware(LoggingMiddleware)

    captured_logs = []

    def mock_destination(log_data):
        captured_logs.append(log_data)

    LOG_DESTINATIONS.append(mock_destination)

    @test_app.get("/test-endpoint")
    def sample_route():
        return {"status": "ok"}

    @test_app.get("/error-endpoint")
    def error_route():
        raise RuntimeError("Erro forçado de teste")

    try:
        client = TestClient(test_app, raise_server_exceptions=False)

        # 1. Teste de fluxo bem-sucedido
        response = client.get("/test-endpoint", headers={"x-request-id": "custom-id-999"})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == "custom-id-999"

        events = [log["event"] for log in captured_logs]
        assert "request.received" in events
        assert "request.finished" in events

        finished_log = next(log for log in captured_logs if log["event"] == "request.finished")
        assert finished_log["request_id"] == "custom-id-999"
        assert finished_log["duration"] is not None
        assert finished_log["duration"] >= 0
        assert finished_log["data"]["status_code"] == 200

        # 2. Teste de endpoint retornando HTTPException 404
        @test_app.get("/not-found-endpoint")
        def not_found_route():
            raise HTTPException(status_code=404, detail="Item não encontrado")

        captured_logs.clear()
        nf_response = client.get("/not-found-endpoint")
        assert nf_response.status_code == 404
        nf_log = next(log for log in captured_logs if log["event"] == "request.finished")
        assert nf_log["data"]["status_code"] == 404
        assert nf_log["level"] == "warning"

        # 3. Teste de fluxo com exceção 500
        captured_logs.clear()
        err_response = client.get("/error-endpoint")
        assert err_response.status_code == 500

        err_events = [log["event"] for log in captured_logs]
        assert "request.received" in err_events
        assert "request.error" in err_events

        error_log = next(log for log in captured_logs if log["event"] == "request.error")
        assert "Erro forçado de teste" in error_log["data"]["error_message"]
        assert error_log["data"]["status_code"] == 500
        assert error_log["level"] == "error"

    finally:
        LOG_DESTINATIONS.remove(mock_destination)
