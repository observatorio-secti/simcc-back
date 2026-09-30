import json
import pytest
import polars as pl
from unittest.mock import AsyncMock

from simcc.v1.services import powerBi_service


@pytest.fixture
def mock_logs_dir(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    export_dir = tmp_path / "powerbi_export"
    export_dir.mkdir()

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setattr("simcc.v1.services.powerBi_service.PATH", str(export_dir))

    # Cria arquivo jsonl com múltiplos tipos de logs
    log_file = log_dir / "2026-09-30.jsonl"
    entries = [
        {
            "timestamp": "2026-09-30T12:00:00Z",
            "level": "info",
            "application": "simcc",
            "environment": "test",
            "hostname": "test-host",
            "category": "http",
            "event": "request.finished",
            "message": "Request finished: GET /v1/test",
            "request_id": "req-1",
            "duration": 45.2,
            "data": {
                "route": "/v1/test",
                "method": "GET",
                "status_code": 200,
                "user_id": "usr-9",
                "error_message": None,
            },
        },
        {
            "timestamp": "2026-09-30T12:01:00Z",
            "level": "error",
            "application": "simcc",
            "environment": "test",
            "hostname": "test-host",
            "category": "database",
            "event": "query.error",
            "message": "Database query error",
            "request_id": "req-1",
            "duration": 120.0,
            "data": {
                "database_name": "simcc_db",
                "operation_name": "get_researchers",
                "error_message": "Deadlock detected",
                "sql": "SELECT 1",
            },
        },
        {
            "timestamp": "2026-09-30T12:02:00Z",
            "level": "info",
            "application": "simcc",
            "environment": "test",
            "hostname": "test-host",
            "category": "routine",
            "event": "routine.finished",
            "message": "Routine finished",
            "request_id": None,
            "duration": 5000.0,
            "data": {
                "routine_name": "sync_capes",
                "error_message": None,
                "items_found": 50,
                "items_succeeded": 50,
                "items_failed": 0,
            },
        },
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return export_dir


@pytest.mark.asyncio
async def test_fat_logs_export(mock_logs_dir):
    session = AsyncMock()
    await powerBi_service.fat_logs(session)

    csv_path = mock_logs_dir / "fat_logs.csv"
    assert csv_path.exists()

    df = pl.read_csv(str(csv_path), separator=";")
    assert len(df) == 3
    assert "log_id" in df.columns
    assert "category" in df.columns
    assert "duration" in df.columns
    assert df["category"].to_list() == ["http", "database", "routine"]


@pytest.mark.asyncio
async def test_fat_logs_http_export(mock_logs_dir):
    session = AsyncMock()
    await powerBi_service.fat_logs_http(session)

    csv_path = mock_logs_dir / "fat_logs_http.csv"
    assert csv_path.exists()

    df = pl.read_csv(str(csv_path), separator=";")
    assert len(df) == 1
    assert df["route"][0] == "/v1/test"
    assert df["method"][0] == "GET"
    assert df["status_code"][0] == 200
    assert df["user_id"][0] == "usr-9"


@pytest.mark.asyncio
async def test_fat_logs_database_export(mock_logs_dir):
    session = AsyncMock()
    await powerBi_service.fat_logs_database(session)

    csv_path = mock_logs_dir / "fat_logs_database.csv"
    assert csv_path.exists()

    df = pl.read_csv(str(csv_path), separator=";")
    assert len(df) == 1
    assert df["database_name"][0] == "simcc_db"
    assert df["operation_name"][0] == "get_researchers"
    assert df["error_message"][0] == "Deadlock detected"


@pytest.mark.asyncio
async def test_fat_logs_routine_export(mock_logs_dir):
    session = AsyncMock()
    await powerBi_service.fat_logs_routine(session)

    csv_path = mock_logs_dir / "fat_logs_routine.csv"
    assert csv_path.exists()

    df = pl.read_csv(str(csv_path))
    assert len(df) == 1
    assert df["routine_name"][0] == "sync_capes"
    assert df["items_found"][0] == 50
    assert df["items_succeeded"][0] == 50
    assert df["items_failed"][0] == 0


@pytest.mark.asyncio
async def test_dim_log_dimensions(mock_logs_dir):
    session = AsyncMock()
    await powerBi_service.dim_log_category(session)
    await powerBi_service.dim_log_event(session)

    cat_path = mock_logs_dir / "dim_log_category.csv"
    evt_path = mock_logs_dir / "dim_log_event.csv"

    assert cat_path.exists()
    assert evt_path.exists()

    df_cat = pl.read_csv(str(cat_path), separator=";")
    df_evt = pl.read_csv(str(evt_path), separator=";")

    assert "http" in df_cat["category"].to_list()
    assert "request.finished" in df_evt["event"].to_list()
