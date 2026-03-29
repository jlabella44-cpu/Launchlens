from listingjet.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-xx")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings()
    assert s.jwt_secret == "test-secret-32-chars-minimum-xx"
    assert "postgresql" in s.database_url


def test_settings_app_env_defaults(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-xx")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings()
    assert s.app_env == "development"
    assert s.log_level == "INFO"
