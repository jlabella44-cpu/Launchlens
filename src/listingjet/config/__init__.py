from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"  # comma-separated allowed origins

    # Database — auto-converts postgresql:// to postgresql+asyncpg:// if needed
    database_url: str
    database_url_sync: str = ""

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 1
    jwt_refresh_expiry_days: int = 7

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters for security")
        return v

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "Settings":
        if not self.use_mock_providers:
            missing = []
            if not self.anthropic_api_key:
                missing.append("ANTHROPIC_API_KEY")
            if not self.google_vision_api_key:
                missing.append("GOOGLE_VISION_API_KEY")
            if missing:
                raise ValueError(
                    f"USE_MOCK_PROVIDERS is false but required provider keys are missing: "
                    f"{', '.join(missing)}. Set them or enable USE_MOCK_PROVIDERS=true."
                )
        return self

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_enterprise: str = ""

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "listingjet-main"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3
    s3_bucket_name: str = "listingjet-dev"
    aws_region: str = "us-east-1"

    # Monitoring
    sentry_dsn: str = ""
    git_sha: str = ""

    # Provider API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_vision_api_key: str = ""
    use_mock_providers: bool = False

    # Google OAuth
    google_oauth_client_id: str = ""

    # ClamAV
    clamav_host: str = "localhost"
    clamav_port: int = 3310

    # OpenTelemetry
    otel_exporter_endpoint: str = ""  # Empty = disabled

    # RESO MLS
    reso_api_url: str = ""
    reso_api_key: str = ""

    # Canva
    canva_api_key: str = ""

    # Credit bundles (Stripe price IDs for one-time purchases)
    stripe_price_credit_bundle_5: str = ""
    stripe_price_credit_bundle_10: str = ""
    stripe_price_credit_bundle_25: str = ""
    stripe_price_credit_bundle_50: str = ""

    # New tier pricing (Stripe price IDs)
    stripe_price_lite: str = ""
    stripe_price_active_agent: str = ""
    stripe_price_team: str = ""
    stripe_price_annual: str = ""

    # Canva OAuth2 (Phase 2 — per-tenant access)
    canva_client_id: str = ""
    canva_client_secret: str = ""

    # ElevenLabs (voiceover)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # Email / Notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@listingjet.ai"
    email_enabled: bool = False
    ses_enabled: bool = False

    # Video (Kling AI)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api.klingai.com"
    video_max_photos: int = 8
    video_score_floor: float = 0.65
    video_clip_duration: int = 5

    # Property Lookup
    attom_api_key: str = ""
    walk_score_api_key: str = ""
    property_lookup_cache_ttl: int = 86400  # 24h
    property_verification_enabled: bool = True
    scraper_rate_limit_seconds: int = 5


settings = Settings()
