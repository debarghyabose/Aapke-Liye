"""Production must refuse unsafe settings before serving anything."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.config import Settings

BACKEND = Path(__file__).resolve().parent.parent

PROD = {
    "APP_ENV": "production",
    "MOCK_SERVICES": "false",
    "DATABASE_URL": "postgresql://u:p@db/aapke_liye",
    "MEMBER1_AI_URL": "http://member1:8001",
    "CORS_ORIGINS": "https://app.example.org",
    "STORAGE_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "STAFF_API_KEYS": "officer-1:" + "k" * 32,
}


def test_valid_production_settings_pass():
    Settings.from_env(PROD).validate()


@pytest.mark.parametrize("change, message", [
    ({"MOCK_SERVICES": "true"}, "MOCK_SERVICES"),
    ({"MOCK_MEMBER1": "true"}, "MOCK_MEMBER1"),
    ({"MOCK_MEMBER3": "true"}, "MOCK_MEMBER3"),
    ({"MEMBER1_AI_URL": ""}, "MEMBER1_AI_URL"),
    ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
    ({"DATABASE_URL": ""}, "DATABASE_URL"),
    ({"STORAGE_ENCRYPTION_KEY": ""}, "STORAGE_ENCRYPTION_KEY is required"),
    ({"STORAGE_ENCRYPTION_KEY": "not-a-key"}, "not a valid Fernet key"),
    ({"STAFF_API_KEYS": ""}, "STAFF_API_KEYS"),
    ({"STAFF_API_KEYS": "officer-1:short"}, "at least 24 characters"),
])
def test_production_refuses(change, message):
    with pytest.raises(RuntimeError, match=message):
        Settings.from_env({**PROD, **change}).validate()


def test_development_allows_mocks():
    Settings.from_env({"APP_ENV": "development", "MOCK_SERVICES": "true"}).validate()


@pytest.mark.parametrize("change, message", [
    ({"MOCK_SERVICES": "true"}, "MOCK_SERVICES=true is not allowed in production"),
    ({"STORAGE_ENCRYPTION_KEY": ""}, "STORAGE_ENCRYPTION_KEY is required in production"),
])
def test_server_process_refuses_to_start(change, message):
    """The real import path (what uvicorn does) must exit with an error."""
    env = {**os.environ, **PROD, **change}
    r = subprocess.run([sys.executable, "-c", "import app.main"], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0
    assert message in r.stderr
