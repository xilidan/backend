import json
import logging
from datetime import datetime
from typing import Any

from domain import ReviewResult, Comment, ReviewRecommendation, CommentSeverity, CommentType


logger = logging.getLogger(__name__)


class InMemoryReviewRepository:
    def __init__(self):
        self.storage: dict[str, dict[str, Any]] = {}
        logger.info("Initialized in-memory review repository")
    
    def _get_key(self, project_id: int, mr_iid: int) -> str:
        return f"{project_id}:{mr_iid}"
    
    async def save(self, result: ReviewResult) -> None:
        key = self._get_key(result.project_id, result.mr_id)
        
        # Serialize to dict
        data = {
            "mr_id": result.mr_id,
            "project_id": result.project_id,
            "summary": result.summary,
            "recommendation": result.recommendation.value,
            "reviewed_at": result.reviewed_at.isoformat(),
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
        
        self.storage[key] = data
        logger.info(f"Saved review result for {key}")
    
    async def get(self, project_id: int, mr_iid: int) -> ReviewResult | None:
        key = self._get_key(project_id, mr_iid)
        data = self.storage.get(key)
        
        if not data:
            logger.debug(f"No review found for {key}")
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
        
        result = ReviewResult(
            mr_id=data["mr_id"],
            project_id=data["project_id"],
            comments=comments,
            summary=data["summary"],
            recommendation=ReviewRecommendation(data["recommendation"]),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
        )
        
        logger.debug(f"Retrieved review for {key}")
        return result
    
    async def list(self, project_id: int) -> list[ReviewResult]:
        results = []
        
        for key, data in self.storage.items():
            if data["project_id"] == project_id:
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
                
                result = ReviewResult(
                    mr_id=data["mr_id"],
                    project_id=data["project_id"],
                    comments=comments,
                    summary=data["summary"],
                    recommendation=ReviewRecommendation(data["recommendation"]),
                    reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
                )
                results.append(result)
        
        logger.info(f"Retrieved {len(results)} reviews for project {project_id}")
        return results


class RedisReviewRepository:    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            logger.info(f"Initialized Redis review repository: {redis_url}")
        except ImportError:
            logger.error("redis package not installed, falling back to in-memory")
            raise
    
    def _get_key(self, project_id: int, mr_iid: int) -> str:
        return f"review:{project_id}:{mr_iid}"
    
    def _get_project_key(self, project_id: int) -> str:
        return f"reviews:project:{project_id}"
    
    async def save(self, result: ReviewResult) -> None:
        key = self._get_key(result.project_id, result.mr_id)
        project_key = self._get_project_key(result.project_id)
        
        data = {
            "mr_id": result.mr_id,
            "project_id": result.project_id,
            "summary": result.summary,
            "recommendation": result.recommendation.value,
            "reviewed_at": result.reviewed_at.isoformat(),
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
        
        await self.redis.set(key, json.dumps(data))
        await self.redis.sadd(project_key, key)
        
        logger.info(f"Saved review result to Redis: {key}")
    
    async def get(self, project_id: int, mr_iid: int) -> ReviewResult | None:
        key = self._get_key(project_id, mr_iid)
        data_str = await self.redis.get(key)
        
        if not data_str:
            return None
        
        data = json.loads(data_str)
        
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
        
        result = ReviewResult(
            mr_id=data["mr_id"],
            project_id=data["project_id"],
            comments=comments,
            summary=data["summary"],
            recommendation=ReviewRecommendation(data["recommendation"]),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
        )
        
        logger.debug(f"Retrieved review from Redis: {key}")
        return result
    
    async def list(self, project_id: int) -> list[ReviewResult]:
        project_key = self._get_project_key(project_id)
        keys = await self.redis.smembers(project_key)
        
        results = []
        for key in keys:
            data_str = await self.redis.get(key)
            if not data_str:
                continue
            
            data = json.loads(data_str)
            
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
            
            result = ReviewResult(
                mr_id=data["mr_id"],
                project_id=data["project_id"],
                comments=comments,
                summary=data["summary"],
                recommendation=ReviewRecommendation(data["recommendation"]),
                reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
            )
            results.append(result)
        
        logger.info(f"Retrieved {len(results)} reviews from Redis for project {project_id}")
        return results
    
    async def close(self):
        await self.redis.close()
