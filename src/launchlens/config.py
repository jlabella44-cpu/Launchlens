from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"  # comma-separated allowed origins

    # Database
    database_url: str
    database_url_sync: str = ""

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_enterprise: str = ""

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "launchlens-main"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3
    s3_bucket_name: str = "launchlens-dev"
    aws_region: str = "us-east-1"

    # Monitoring
    sentry_dsn: str = ""
    git_sha: str = ""

    # Feature flags
    shadow_review_enabled: bool = True
    shadow_review_max_listings: int = 100

    # Provider API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_vision_api_key: str = ""
    use_mock_providers: bool = False

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
    email_from: str = "noreply@launchlens.com"
    email_enabled: bool = False

    # Video (Kling AI)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api.klingai.com"
    video_max_photos: int = 8
    video_score_floor: float = 0.65
    video_clip_duration: int = 5


settings = Settings()
