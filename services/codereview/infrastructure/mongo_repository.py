import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from domain import ReviewResult, Comment, ReviewRecommendation, CommentSeverity, CommentType, UserRating


logger = logging.getLogger(__name__)


class MongoUserRepository:
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.collection = self.db.users
        logger.info(f"Initialized MongoDB user repository: {mongo_url}/{db_name}")
    
    async def get_user_rating(self, email: str) -> UserRating | None:
        data = await self.collection.find_one({"email": email})
        if not data:
            return None
        
        return UserRating(
            email=data["email"],
            rating=data["rating"],
            review_count=data.get("review_count", 0),
            last_updated=data.get("last_updated", datetime.utcnow()),
        )
    
    async def save_user_rating(self, user_rating: UserRating) -> None:
        await self.collection.update_one(
            {"email": user_rating.email},
            {
                "$set": {
                    "email": user_rating.email,
                    "rating": user_rating.rating,
                    "review_count": user_rating.review_count,
                    "last_updated": user_rating.last_updated,
                }
            },
            upsert=True
        )
        logger.info(f"Saved user rating for {user_rating.email}: {user_rating.rating}")


class MongoReviewRepository:
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.collection = self.db.reviews
        logger.info(f"Initialized MongoDB review repository: {mongo_url}/{db_name}")
    
    def _get_key(self, project_id: int, mr_iid: int) -> str:
        return f"{project_id}:{mr_iid}"
    
    async def save(self, result: ReviewResult) -> None:
        key = self._get_key(result.project_id, result.mr_id)
        
        data = {
            "key": key,
            "mr_id": result.mr_id,
            "project_id": result.project_id,
            "summary": result.summary,
            "recommendation": result.recommendation.value,
            "quality_score": result.quality_score,
            "reviewed_at": result.reviewed_at,
            "comments": [
                {
                    "file_path": c.file_path,
                    "line": c.line,
                    "content": c.content,
                    "severity": c.severity.value,
                    "type": c.type.value,
                }
                for c in result.comments
            ],
        }
        
        await self.collection.update_one(
            {"key": key},
            {"$set": data},
            upsert=True
        )
        logger.info(f"Saved review result to MongoDB: {key}")
    
    async def get(self, project_id: int, mr_iid: int) -> ReviewResult | None:
        key = self._get_key(project_id, mr_iid)
        data = await self.collection.find_one({"key": key})
        
        if not data:
            return None
        
        comments = [
            Comment(
                file_path=c["file_path"],
                line=c["line"],
                content=c["content"],
                severity=CommentSeverity(c["severity"]),
                type=CommentType(c["type"]),
            )
            for c in data["comments"]
        ]
        
        return ReviewResult(
            mr_id=data["mr_id"],
            project_id=data["project_id"],
            comments=comments,
            summary=data["summary"],
            recommendation=ReviewRecommendation(data["recommendation"]),
            reviewed_at=data["reviewed_at"],
            quality_score=data.get("quality_score", 0),
        )
