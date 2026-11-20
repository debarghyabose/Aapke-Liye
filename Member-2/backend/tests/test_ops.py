"""Phase 5: migrations, /health, request IDs and JSON logs."""
import json
import logging
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.logs import JsonFormatter, request_id_var
from conftest import DB_FILE, DOWN, new_claim

BACKEND = Path(__file__).resolve().parent.parent


def alembic(*args, url):
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=120)


def test_migrations_create_exactly_the_model_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    up = alembic("upgrade", "head", url=url)
    assert up.returncode == 0, up.stderr
    check = alembic("check", url=url)          # fails if models and migrations differ
    assert check.returncode == 0, check.stdout + check.stderr


def test_migration_sql_compiles_for_postgres():
    r = alembic("upgrade", "head", "--sql", url="postgresql://u:p@localhost/aapke_liye")
    assert r.returncode == 0, r.stderr
    assert "CREATE TABLE claims" in r.stdout and "CREATE TABLE audit_log" in r.stdout


def test_health_reports_db_services_and_rules(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "ok"
    assert body["member1_ai"] == "ok" and body["member3_verify"] == "ok"
    assert body["rules_version"]


def test_health_when_member1_is_down(client, services):
    services.m1_health.side_effect = DOWN
    r = client.get("/health")
    assert r.status_code == 200                     # still serving; degraded is reported
    assert r.json()["member1_ai"] == "unreachable"


def test_request_id_is_returned_forwarded_and_audited(client, services):
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/audio", headers={**h, "X-Request-ID": "trace-123"},
                    files={"audio": ("a.webm", b"\x1a\x45\xdf\xa3x", "audio/webm")})
    assert r.headers["X-Request-ID"] == "trace-123"
    assert services.m1.calls.last.request.headers["X-Request-ID"] == "trace-123"
    with sqlite3.connect(DB_FILE) as db:
        ids = {row[0] for row in db.execute(
            "SELECT request_id FROM audit_log WHERE claim_id = ? AND action = 'audio_processed'",
            (cid,))}
    assert ids == {"trace-123"}


def test_unsafe_request_id_is_replaced(client):
    r = client.get("/health", headers={"X-Request-ID": "bad id\nwith newline"})
    assert r.headers["X-Request-ID"] != "bad id\nwith newline"
    assert len(r.headers["X-Request-ID"]) == 32


def test_json_log_format():
    token = request_id_var.set("rid-1")
    try:
        record = logging.LogRecord("app", logging.INFO, __file__, 1, "request", (), None)
        record.status = 200
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["message"] == "request" and line["request_id"] == "rid-1"
    assert line["status"] == 200 and line["time"].endswith("Z")
