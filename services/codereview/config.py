import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    
    service_name: str = "codereview"
    service_host: str = "0.0.0.0"
    service_port: int = 8000
    log_level: str = "INFO"
    
    gitlab_url: str = os.getenv("GITLAB_URL", "https://gitlab.com")
    gitlab_token: str = os.getenv("GITLAB_TOKEN", "")
    
    llm_provider: str = os.getenv("LLM_PROVIDER_NAME", "azure_openai")  # openai, anthropic, azure_openai
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    azure_config_path: str = os.getenv("AZURE_CONFIG_PATH", "instance.json")
    use_mock_llm: bool = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    
    repository_type: str = os.getenv("REPOSITORY_TYPE", "memory")  # memory, redis, mongo
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://mongo:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "codereview")
    
    development_standards: list[str] = [
        "Follow PEP 8 style guide",
        "Write clear and concise comments",
        "Ensure proper error handling",
        "Avoid code duplication",
        "Write unit tests for new functionality",
        "Use type hints",
        "Follow SOLID principles",
        "Ensure code is secure and follows best practices",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
