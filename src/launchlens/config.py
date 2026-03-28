from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"

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

    # Video (Kling AI)
    kling_access_key: str = ""
    kling_secret_key: str = ""
    kling_api_base_url: str = "https://api.klingai.com"
    video_max_photos: int = 8
    video_score_floor: float = 0.65
    video_clip_duration: int = 5


settings = Settings()
