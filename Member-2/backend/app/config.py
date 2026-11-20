"""All settings come from environment variables (or a .env file). See .env.example."""
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = BASE_DIR / "rules"
FONTS_DIR = BASE_DIR / "fonts"

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "mr", "ta"]  # English + top 5


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _list(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _staff_keys(value: str | None) -> dict[str, str]:
    """"label:key,label2:key2" -> {label: key}. The label (never the key) goes in the audit log.
    A key without a label is named by a short fingerprint."""
    keys = {}
    for item in _list(value):
        label, _, key = item.rpartition(":")
        keys[label.strip() or "key-" + hashlib.sha256(key.encode()).hexdigest()[:8]] = key.strip()
    return keys


@dataclass
class Settings:
    app_env: str = "development"
    mock_services: bool = False      # shortcut: turns both mocks on
    mock_member1: bool = False
    mock_member3: bool = False
    database_url: str = ""
    storage_dir: Path = BASE_DIR / "storage"
    member1_ai_url: str = ""
    member3_verify_url: str = ""
    member3_dashboard_key: str = ""   # Member 3's DASHBOARD_API_KEY, for the officials' map
    service_timeout: float = 30.0
    cors_origins: list[str] = field(default_factory=list)
    storage_encryption_keys: list[str] = field(default_factory=list)
    staff_api_keys: dict[str, str] = field(default_factory=dict)   # label -> key
    rate_limit_create: str = "10/minute"
    rate_limit_upload: str = "30/minute"
    log_level: str = "INFO"
    digilocker_mode: str = "mock"   # only "mock" exists this sprint

    @property
    def use_mock_member1(self) -> bool:
        return self.mock_services or self.mock_member1

    @property
    def use_mock_member3(self) -> bool:
        return self.mock_services or self.mock_member3

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls, env=os.environ) -> "Settings":
        return cls(
            app_env=env.get("APP_ENV", "development").strip().lower(),
            mock_services=_bool(env.get("MOCK_SERVICES")),
            mock_member1=_bool(env.get("MOCK_MEMBER1")),
            mock_member3=_bool(env.get("MOCK_MEMBER3")),
            database_url=env.get("DATABASE_URL", "").strip(),
            storage_dir=Path(env.get("STORAGE_DIR") or BASE_DIR / "storage"),
            member1_ai_url=env.get("MEMBER1_AI_URL", "").strip().rstrip("/"),
            member3_verify_url=env.get("MEMBER3_VERIFY_URL", "").strip().rstrip("/"),
            member3_dashboard_key=env.get("MEMBER3_DASHBOARD_KEY", "").strip(),
            service_timeout=float(env.get("SERVICE_TIMEOUT_SECONDS") or 30),
            cors_origins=_list(env.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")),
            storage_encryption_keys=_list(env.get("STORAGE_ENCRYPTION_KEY")),
            staff_api_keys=_staff_keys(env.get("STAFF_API_KEYS")),
            rate_limit_create=env.get("RATE_LIMIT_CREATE") or "10/minute",
            rate_limit_upload=env.get("RATE_LIMIT_UPLOAD") or "30/minute",
            log_level=env.get("LOG_LEVEL") or "INFO",
            digilocker_mode=(env.get("DIGILOCKER_MODE") or "mock").strip().lower(),
        )

    def validate(self) -> None:
        """Refuse to start with settings that are unsafe for real users."""
        if self.app_env not in ("development", "production"):
            raise RuntimeError("APP_ENV must be 'development' or 'production'")
        from cryptography.fernet import Fernet

        problems = []
        try:
            for key in self.storage_encryption_keys:
                Fernet(key)
        except ValueError:
            problems.append("STORAGE_ENCRYPTION_KEY is not a valid Fernet key")

        if self.is_production:
            checks = {
                "MOCK_SERVICES=true is not allowed in production": self.mock_services,
                "MOCK_MEMBER1=true is not allowed in production": self.mock_member1,
                "MOCK_MEMBER3=true is not allowed in production": self.mock_member3,
                "MEMBER1_AI_URL is required in production": not self.member1_ai_url,
                "DATABASE_URL (Postgres) is required in production": not self.database_url,
                "CORS_ORIGINS must be an explicit list of origins in production":
                    not self.cors_origins or "*" in self.cors_origins,
                "STORAGE_ENCRYPTION_KEY is required in production":
                    not self.storage_encryption_keys,
                "STAFF_API_KEYS is required in production": not self.staff_api_keys,
                "every STAFF_API_KEYS key must be at least 24 characters":
                    any(len(k) < 24 for k in self.staff_api_keys.values()),
            }
            problems += [message for message, failed in checks.items() if failed]
        if problems:
            raise RuntimeError("Refusing to start: " + "; ".join(problems))

    @property
    def async_database_url(self) -> str:
        """URL for the app (async drivers). SQLite file in the project folder by default."""
        url = self.database_url or f"sqlite:///{BASE_DIR / 'aapke_liye.db'}"
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if url.startswith(("postgresql://", "postgres://")):
            return "postgresql+psycopg://" + url.split("://", 1)[1]
        return url

    @property
    def sync_database_url(self) -> str:
        """URL for Alembic (sync drivers)."""
        return self.async_database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)


settings = Settings.from_env()
