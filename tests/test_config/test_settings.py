from listingjet.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-required!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings()
    assert s.jwt_secret == "test-secret-32-chars-minimum-required!"
    assert "postgresql" in s.database_url


def test_settings_app_env_defaults(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-required!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings()
    assert s.app_env == "development"
    assert s.log_level == "INFO"


def test_settings_ffmpeg_bin_overridable(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-required!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings(ffmpeg_bin="x")
    assert s.ffmpeg_bin == "x"


def test_settings_video_fields_are_runway_only(monkeypatch):
    """The pre-Runway video provider is gone — no settings of its own survive.

    Asserted as an exhaustive set rather than name-by-name so any resurrected
    legacy field (access keys, base urls, score floors) fails here.
    """
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-required!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    s = Settings()
    video_fields = {f for f in type(s).model_fields if "video" in f or "runway" in f}
    assert video_fields == {
        "runway_api_key",
        "runway_interior_model",
        "runway_exterior_model",
        "video_music_enabled",
        "video_music_path",
    }


def test_settings_video_two_tier_defaults(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-required!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
    # ffmpeg_bin's default ("ffmpeg") is overridden by the repo's own .env
    # (FFMPEG_BIN points at the portable build) — not asserted here; see
    # test_settings_ffmpeg_bin_overridable for the field itself.
    s = Settings()
    assert s.runway_api_key == ""
    assert s.runway_interior_model == "gen4_turbo"
    assert s.runway_exterior_model == "veo3.1_fast"
    assert s.video_music_enabled is False
    assert s.video_music_path == ""
