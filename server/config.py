from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Check server/.env first, then parent .env
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    gemini_api_key: str = ""  # unused, kept for backward compat with existing .env files
    mistral_api_key: str = ""
    github_token: str = ""

    # Bote's pipeline
    fal_key: str = ""
    runware_api_key: str = ""

    # Supabase — for updating video_requests status
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Default avatar image (fal.ai public URL — no upload needed)
    avatar_image_url: str = (
        "https://v3.fal.media/files/koala/NLVPfOI4XL1cWT2PmmqT3_Hope.png"
    )

    @property
    def llm_provider(self) -> str:
        return "mistral"


settings = Settings()
