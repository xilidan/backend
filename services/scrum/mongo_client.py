from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from datetime import datetime
from typing import List, Dict, Any, Optional

class MongoClient:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.chat_history = self.db.chat_history
        self.jira_cache = self.db.jira_cache

    async def save_message(self, session_id: str, role: str, content: str):
        """Save a chat message to history."""
        await self.chat_history.insert_one({
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })

    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve chat history for a session."""
        cursor = self.chat_history.find(
            {"session_id": session_id}
        ).sort("timestamp", 1).limit(limit) # Get oldest first? No, usually we want context window.
        # If we sort by timestamp ascending, we get the conversation flow.
        # But if we limit, we might want the *latest* 50.
        # So sort desc, limit, then reverse.
        
        cursor = self.chat_history.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        return sorted(history, key=lambda x: x["timestamp"])

    async def cache_jira_issues(self, issues: List[Dict[str, Any]]):
        """Cache Jira issues, replacing existing ones."""
        if not issues:
            return
            
        # Clear existing cache or upsert?
        # For simplicity, let's clear and insert fresh batch if we are syncing all.
        # Or use bulk write to upsert based on key.
        
        from pymongo import UpdateOne
        
        operations = []
        for issue in issues:
            key = issue.get("key")
            if key:
                operations.append(
                    UpdateOne(
                        {"key": key},
                        {"$set": issue},
                        upsert=True
                    )
                )
        
        if operations:
            await self.jira_cache.bulk_write(operations)

    async def get_cached_issues(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get cached Jira issues."""
        # Ideally we would filter by relevance, but for now return recent ones
        cursor = self.jira_cache.find().limit(limit)
        return await cursor.to_list(length=limit)
