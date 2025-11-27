import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import get_settings
from delivery import router, set_review_usecase
from infrastructure import (
    GitLabClientImpl,
    LLMClientImpl,
    MockLLMClient,
    InMemoryReviewRepository,
    RedisReviewRepository,
    MongoUserRepository,
    MongoReviewRepository,
)
from usecase import ReviewUsecase


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


review_usecase_instance: ReviewUsecase | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global review_usecase_instance
    
    settings = get_settings()
    logger.info(f"Starting {settings.service_name} service")
    
    logging.getLogger().setLevel(settings.log_level)
    
    logger.info("Initializing infrastructure...")
    
    gitlab_client = GitLabClientImpl(
        url=settings.gitlab_url,
        private_token=settings.gitlab_token,
    )
    
    if settings.use_mock_llm:
        logger.info("Using mock LLM client")
        llm_client = MockLLMClient()
    else:
        llm_client = LLMClientImpl(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model or None,
            azure_config_path=settings.azure_config_path if settings.llm_provider == "azure_openai" else None,
        )
    
    if settings.repository_type == "redis":
        logger.info(f"Using Redis repository: {settings.redis_url}")
        repository = RedisReviewRepository(redis_url=settings.redis_url)
    elif settings.repository_type == "mongo":
        logger.info(f"Using Mongo repository: {settings.mongo_url}")
        repository = MongoReviewRepository(
            mongo_url=settings.mongo_url,
            db_name=settings.mongo_db_name,
        )
    else:
        logger.info("Using in-memory repository")
        repository = InMemoryReviewRepository()
    
    # Initialize User Repository (always Mongo for now)
    user_repository = MongoUserRepository(
        mongo_url=settings.mongo_url,
        db_name=settings.mongo_db_name,
    )
    
    review_usecase_instance = ReviewUsecase(
        gitlab_client=gitlab_client,
        llm_client=llm_client,
        repository=repository,
        user_repository=user_repository,
        development_standards=settings.development_standards,
    )
    
    set_review_usecase(review_usecase_instance)
    
    logger.info("Service initialized successfully")
    
    yield
    
    logger.info("Shutting down service...")
    if settings.repository_type == "redis" and hasattr(repository, "close"):
        await repository.close()


app = FastAPI(
    title="Code Review Service",
    description="AI-powered code review assistant for GitLab Merge Requests",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Code Review Service",
        "version": "1.0.0",
        "status": "running",
    }


def main():
    settings = get_settings()
    
    logger.info(
        f"Starting server on {settings.service_host}:{settings.service_port}"
    )
    
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
