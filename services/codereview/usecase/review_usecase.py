import logging
from datetime import datetime

from domain import (
    MergeRequest,
    ReviewResult,
    Comment,
    ReviewRecommendation,
    GitLabClient,
    LLMClient,
    ReviewRepository,
    UserRating,
)
from infrastructure.mongo_repository import MongoUserRepository, MongoReviewRepository


logger = logging.getLogger(__name__)


class ReviewUsecase:
    def __init__(
        self,
        gitlab_client: GitLabClient,
        llm_client: LLMClient,
        repository: ReviewRepository,
        user_repository: MongoUserRepository,
        development_standards: list[str] | None = None,
    ):
        self.gitlab_client = gitlab_client
        self.llm_client = llm_client
        self.repository = repository
        self.user_repository = user_repository
        self.development_standards = development_standards or [
            "Follow PEP 8 style guide",
            "Write clear and concise comments",
            "Ensure proper error handling",
            "Avoid code duplication",
            "Write unit tests for new functionality",
            "Use type hints",
        ]
    
    async def review_merge_request(self, project_id: int, mr_iid: int) -> ReviewResult:
        logger.info(f"Starting review for MR {project_id}/{mr_iid}")
        
        mr = await self.gitlab_client.get_merge_request(project_id, mr_iid)
        file_diffs = await self.gitlab_client.get_merge_request_diff(project_id, mr_iid)
        
        logger.info(f"Analyzing {len(file_diffs)} file(s) in MR '{mr.title}'")
        
        comments, summary, recommendation, quality_score = await self.llm_client.analyze_code(
            mr_title=mr.title,
            mr_description=mr.description,
            file_diffs=file_diffs,
            standards=self.development_standards,
        )
        
        # Handle user rating
        if mr.author_email:
            await self._update_user_rating(mr.author_email, quality_score)
        
        result = ReviewResult(
            mr_id=mr_iid,  # Use mr_iid (project-scoped) not mr.id (global)
            project_id=project_id,
            comments=comments,
            summary=summary,
            recommendation=recommendation,
            reviewed_at=datetime.utcnow(),
            quality_score=quality_score,
        )
        
        await self.repository.save(result)
        
        logger.info(
            f"Review completed: {len(comments)} comments, "
            f"recommendation: {recommendation.value}, score: {quality_score}"
        )
        
        return result
    
    async def _update_user_rating(self, email: str, quality_score: int) -> None:
        user_rating = await self.user_repository.get_user_rating(email)
        
        if not user_rating:
            logger.info(f"Creating new user rating for {email}")
            user_rating = UserRating(email=email, rating=500, review_count=0)
        
        # Simple rating update logic: +/- from base 50
        # If score > 50, rating increases. If score < 50, rating decreases.
        rating_change = quality_score - 50
        new_rating = user_rating.rating + rating_change
        
        user_rating.rating = new_rating
        user_rating.review_count += 1
        user_rating.last_updated = datetime.utcnow()
        
        await self.user_repository.save_user_rating(user_rating)
        logger.info(f"Updated rating for {email}: {user_rating.rating} (change: {rating_change})")

    async def post_review_to_gitlab(self, project_id: int, mr_iid: int) -> None:
        logger.info(f"Posting review to GitLab for MR {project_id}/{mr_iid}")
        
        result = await self.repository.get(project_id, mr_iid)
        if not result:
            logger.error(f"No review found for MR {project_id}/{mr_iid}")
            return
        
        for comment in result.comments:
            try:
                await self.gitlab_client.post_comment(project_id, mr_iid, comment)
                logger.debug(f"Posted comment: {comment.file_path}:{comment.line}")
            except Exception as e:
                logger.error(f"Failed to post comment: {e}")
        
        summary_md = result.to_summary_markdown()
        await self.gitlab_client.post_summary_note(project_id, mr_iid, summary_md)
        
        labels = self._get_labels_for_recommendation(result.recommendation)
        await self.gitlab_client.update_labels(project_id, mr_iid, labels)
        
        logger.info(f"Review posted successfully with labels: {labels}")
    
    def _get_labels_for_recommendation(
        self, recommendation: ReviewRecommendation
    ) -> list[str]:
        label_map = {
            ReviewRecommendation.MERGE: ["ai-reviewed", "ready-for-merge"],
            ReviewRecommendation.NEEDS_FIXES: ["ai-reviewed", "needs-review", "changes-requested"],
            ReviewRecommendation.REJECT: ["ai-reviewed", "needs-review", "rejected"],
        }
        return label_map.get(recommendation, ["ai-reviewed"])
    
    async def process_webhook_event(
        self, project_id: int, mr_iid: int, action: str
    ) -> None:
        logger.info(f"Processing webhook event: {action} for MR {project_id}/{mr_iid}")
        
        if action not in ["open", "update", "reopen", "manual"]:
            logger.info(f"Ignoring action: {action}")
            return
        
        try:
            await self.review_merge_request(project_id, mr_iid)
            
            await self.post_review_to_gitlab(project_id, mr_iid)
            
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}", exc_info=True)
            raise
