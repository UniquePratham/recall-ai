"""
Configuration management for Recall AI
"""
import os
from typing import List, Optional, Literal
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Supported AI providers
ProviderType = Literal["OpenAI", "Gemini", "Claude", "GitHub", "Custom"]


@dataclass
class DatabaseConfig:
    """Database configuration"""
    mongodb_uri: str
    db_name: str

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            mongodb_uri=os.getenv('MONGODB_URI', 'mongodb://localhost:27017'),
            db_name=os.getenv('DB_NAME', 'recall_ai')
        )


@dataclass
class AIConfig:
    """AI service configuration"""
    provider: ProviderType
    model: str
    embedding_model: str

    # Provider-specific API keys
    openai_api_key: str
    gemini_api_key: str
    claude_api_key: str
    github_token: str

    # Custom provider settings
    custom_api_url: str
    custom_api_key: str

    # Qdrant configuration
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str
    qdrant_timeout: int
    qdrant_prefer_grpc: bool

    @classmethod
    def from_env(cls) -> 'AIConfig':
        return cls(
            provider=os.getenv('AI_PROVIDER', 'OpenAI'),
            model=os.getenv('AI_MODEL', 'gemini-1.5-pro-latest' if os.getenv('AI_PROVIDER', 'OpenAI') == 'Gemini' else 'gpt-3.5-turbo'),
            embedding_model=os.getenv(
                'EMBEDDING_MODEL', 'text-embedding-004' if os.getenv('AI_PROVIDER', 'OpenAI') == 'Gemini' else 'text-embedding-ada-002'),

            # API Keys
            openai_api_key=os.getenv('OPENAI_API_KEY', ''),
            gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
            claude_api_key=os.getenv('CLAUDE_API_KEY', ''),
            github_token=os.getenv('GITHUB_TOKEN', ''),

            # Custom provider
            custom_api_url=os.getenv('CUSTOM_API_URL', ''),
            custom_api_key=os.getenv('CUSTOM_API_KEY', ''),

            # Qdrant Cloud
            qdrant_url=os.getenv(
                'QDRANT_URL', 'https://your-cluster-url.qdrant.tech:6333'),
            qdrant_api_key=os.getenv('QDRANT_API_KEY', ''),
            qdrant_collection_name=os.getenv(
                'QDRANT_COLLECTION_NAME', 'recall_documents'),
            qdrant_timeout=int(os.getenv('QDRANT_TIMEOUT', '30')),
            qdrant_prefer_grpc=os.getenv(
                'QDRANT_PREFER_GRPC', 'false').lower() == 'true'
        )

    def get_api_key(self) -> str:
        """Get API key for the selected provider"""
        provider_keys = {
            "OpenAI": self.openai_api_key,
            "Gemini": self.gemini_api_key,
            "Claude": self.claude_api_key,
            "GitHub": self.github_token,
            "Custom": self.custom_api_key
        }
        return provider_keys.get(self.provider, '')

    def get_base_url(self) -> Optional[str]:
        """Get base URL for the selected provider"""
        provider_urls = {
            "OpenAI": "https://api.openai.com/v1",
            "Gemini": "https://generativelanguage.googleapis.com/v1",
            "Claude": "https://api.anthropic.com",
            "GitHub": "https://models.inference.ai.azure.com",
            "Custom": self.custom_api_url
        }
        return provider_urls.get(self.provider)


@dataclass
class AppConfig:
    """Application configuration"""
    bot_token: str
    log_level: str
    max_file_size_mb: int
    max_audio_duration_minutes: int
    rate_limit_requests_per_minute: int
    secret_key: str
    license_key: str
    owner_telegram_id: int
    allowed_file_types: List[str]

    # Feature flags
    enable_web_scraping: bool
    enable_audio_processing: bool
    enable_image_processing: bool

    @classmethod
    def from_env(cls) -> 'AppConfig':
        allowed_types = os.getenv(
            'ALLOWED_FILE_TYPES', 'pdf,docx,txt,jpg,jpeg,png,mp3,wav,ogg')
        return cls(
            bot_token=os.getenv('BOT_TOKEN', ''),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '50')),
            max_audio_duration_minutes=int(
                os.getenv('MAX_AUDIO_DURATION_MINUTES', '10')),
            rate_limit_requests_per_minute=int(
                os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '20')),
            secret_key=os.getenv('SECRET_KEY', ''),
            license_key=os.getenv('LICENSE_KEY', ''),
            owner_telegram_id=int(os.getenv('OWNER_TELEGRAM_ID', '0')),
            allowed_file_types=[t.strip() for t in allowed_types.split(',')],
            enable_web_scraping=os.getenv(
                'ENABLE_WEB_SCRAPING', 'true').lower() == 'true',
            enable_audio_processing=os.getenv(
                'ENABLE_AUDIO_PROCESSING', 'true').lower() == 'true',
            enable_image_processing=os.getenv(
                'ENABLE_IMAGE_PROCESSING', 'true').lower() == 'true'
        )


@dataclass
class Config:
    """Main configuration class"""
    app: AppConfig
    database: DatabaseConfig
    ai: AIConfig

    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            app=AppConfig.from_env(),
            database=DatabaseConfig.from_env(),
            ai=AIConfig.from_env()
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if not self.app.bot_token:
            errors.append("BOT_TOKEN is required")

        # Check if API key exists for selected provider
        api_key = self.ai.get_api_key()
        if not api_key:
            errors.append(
                f"API key required for provider '{self.ai.provider}'")

        if not self.database.mongodb_uri:
            errors.append("MONGODB_URI is required")

        if not self.ai.qdrant_url:
            errors.append("QDRANT_URL is required")

        if not self.app.secret_key:
            errors.append("SECRET_KEY is required")

        return errors


# Global config instance
config = Config.from_env()
