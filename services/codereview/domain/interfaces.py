from abc import ABC, abstractmethod
from typing import Protocol

from .entities import (
    MergeRequest,
    FileDiff,
    Comment,
    ReviewResult,
    ReviewRecommendation,
)


class GitLabClient(Protocol):
    
    async def get_merge_request(self, project_id: int, mr_iid: int) -> MergeRequest:
        ...
    
    async def get_merge_request_diff(self, project_id: int, mr_iid: int) -> list[FileDiff]:
        ...
    
    async def post_comment(self, project_id: int, mr_iid: int, comment: Comment) -> None:
        ...
    
    async def update_labels(self, project_id: int, mr_iid: int, labels: list[str]) -> None:
        ...
    
    async def post_summary_note(self, project_id: int, mr_iid: int, content: str) -> None:
        ...


class LLMClient(Protocol):
    
    async def analyze_code(
        self,
        mr_title: str,
        mr_description: str,
        file_diffs: list[FileDiff],
        standards: list[str]
    ) -> tuple[list[Comment], str, ReviewRecommendation]:
        ...


class ReviewRepository(Protocol):
    
    async def save(self, result: ReviewResult) -> None:
        ...
    
    async def get(self, project_id: int, mr_iid: int) -> ReviewResult | None:
        ...
    
    async def list(self, project_id: int) -> list[ReviewResult]:
        ...
