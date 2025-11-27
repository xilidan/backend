import logging
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from usecase import ReviewUsecase


logger = logging.getLogger(__name__)


class MergeRequestWebhook(BaseModel):
    object_kind: str
    event_type: str | None = None
    object_attributes: dict
    project: dict


router = APIRouter()


review_usecase: ReviewUsecase | None = None


def set_review_usecase(usecase: ReviewUsecase):
    global review_usecase
    review_usecase = usecase


@router.post("/webhooks/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        payload = await request.json()
        
        logger.info(f"Received GitLab webhook: {payload.get('object_kind', 'unknown')}")
        
        if payload.get("object_kind") != "merge_request":
            logger.info(f"Ignoring non-MR event: {payload.get('object_kind')}")
            return {"status": "ignored", "reason": "not a merge request event"}
        
        attrs = payload.get("object_attributes", {})
        project = payload.get("project", {})
        
        project_id = project.get("id")
        mr_iid = attrs.get("iid")
        action = attrs.get("action")
        
        user = payload.get("user", {})
        trigger_user_email = user.get("email")
        
        if not project_id or not mr_iid:
            logger.error("Missing project_id or mr_iid in webhook payload")
            raise HTTPException(status_code=400, detail="Invalid webhook payload")
        
        logger.info(f"Processing MR {project_id}/{mr_iid}, action: {action}, triggered by: {trigger_user_email}")
        
        if review_usecase:
            background_tasks.add_task(
                review_usecase.process_webhook_event,
                project_id,
                mr_iid,
                action,
                trigger_user_email,
            )
        else:
            logger.error("Review usecase not initialized")
            raise HTTPException(status_code=500, detail="Service not initialized")
        
        return {
            "status": "accepted",
            "project_id": project_id,
            "mr_iid": mr_iid,
            "action": action,
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "codereview",
        "version": "1.0.0",
    }


@router.get("/reviews/{project_id}/{mr_iid}")
async def get_review(project_id: int, mr_iid: int):
    if not review_usecase:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = await review_usecase.repository.get(project_id, mr_iid)
    
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return {
        "project_id": result.project_id,
        "mr_id": result.mr_id,
        "summary": result.summary,
        "recommendation": result.recommendation.value,
        "comments_count": len(result.comments),
        "reviewed_at": result.reviewed_at.isoformat(),
    }


@router.post("/reviews/{project_id}/{mr_iid}/trigger")
async def trigger_review(
    project_id: int,
    mr_iid: int,
    background_tasks: BackgroundTasks,
):
    if not review_usecase:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    logger.info(f"Manual review triggered for MR {project_id}/{mr_iid}")
    
    background_tasks.add_task(
        review_usecase.process_webhook_event,
        project_id,
        mr_iid,
        "manual",
        None,  # No trigger user email for manual trigger yet
    )
    
    return {
        "status": "triggered",
        "project_id": project_id,
        "mr_iid": mr_iid,
    }


@router.get("/users/{email}/rating")
async def get_user_rating(email: str):
    if not review_usecase:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    rating = await review_usecase.user_repository.get_user_rating(email)
    
    if not rating:
        raise HTTPException(status_code=404, detail="User rating not found")
    
    return {
        "email": rating.email,
        "rating": rating.rating,
        "review_count": rating.review_count,
        "last_updated": rating.last_updated.isoformat(),
    }
