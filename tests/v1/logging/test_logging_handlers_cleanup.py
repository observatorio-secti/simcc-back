import json
import os
import sys
from datetime import datetime, timedelta
from io import StringIO

from simcc.core.logging.cleanup import clean_old_logs
from simcc.core.logging.handlers import write_to_console, write_to_file, dispatch_log, LOG_DESTINATIONS


def test_write_to_file(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr("simcc.core.logging.handlers.LOG_DIR", str(log_dir))

    sample_log = {
        "timestamp": "2026-09-30T10:00:00Z",
        "level": "info",
        "event": "test.file_write",
        "message": "Gravando log em arquivo",
        "data": {"count": 42},
    }

    write_to_file(sample_log)

    today_str = datetime.now().strftime("%Y-%m-%d")
    expected_file = log_dir / f"{today_str}.jsonl"

    assert expected_file.exists()

    with open(expected_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["event"] == "test.file_write"
    assert parsed["data"]["count"] == 42


def test_write_to_console():
    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        sample_log = {"level": "info", "event": "console.test"}
        write_to_console(sample_log)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "console.test" in output
    parsed = json.loads(output.strip())
    assert parsed["level"] == "info"


def test_clean_old_logs(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Cria arquivo antigo por nome (ex: 15 dias atrás)
    old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    old_file = log_dir / f"{old_date}.jsonl"
    old_file.write_text('{"event": "old"}')

    # Cria arquivo recente (ex: 2 dias atrás)
    recent_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    recent_file = log_dir / f"{recent_date}.jsonl"
    recent_file.write_text('{"event": "recent"}')

    # Cria arquivo de hoje
    today_date = datetime.now().strftime("%Y-%m-%d")
    today_file = log_dir / f"{today_date}.jsonl"
    today_file.write_text('{"event": "today"}')

    # Executa limpeza com retenção de 7 dias
    deleted = clean_old_logs(log_dir=str(log_dir), max_age_days=7)

    assert str(old_file) in deleted
    assert not old_file.exists()
    assert recent_file.exists()
    assert today_file.exists()
