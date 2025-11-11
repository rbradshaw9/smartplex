"""
Feedback API endpoints for user feedback, bug reports, and feature requests.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.supabase import get_supabase_client, get_current_user

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    """Request model for creating feedback."""
    feedback_type: str = Field(..., pattern="^(bug|feature|improvement|other)$")
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    screenshot_url: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response model for feedback."""
    id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    feedback_type: str
    title: str
    description: str
    page_url: Optional[str]
    status: str
    priority: str
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class FeedbackUpdate(BaseModel):
    """Request model for updating feedback (admin only)."""
    status: Optional[str] = Field(None, pattern="^(new|reviewing|in-progress|resolved|closed)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    admin_notes: Optional[str] = None


@router.post("", response_model=FeedbackResponse)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Submit feedback, bug report, or feature request.
    
    Available during beta for user feedback collection.
    """
    supabase = get_supabase_client()
    
    # Insert feedback
    result = supabase.table("feedback").insert({
        "user_id": current_user["id"],
        "user_email": current_user.get("email"),
        "feedback_type": feedback.feedback_type,
        "title": feedback.title,
        "description": feedback.description,
        "page_url": feedback.page_url,
        "user_agent": feedback.user_agent,
        "screenshot_url": feedback.screenshot_url,
        "status": "new",
        "priority": "medium"
    }).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create feedback")
    
    return result.data[0]


@router.get("", response_model=List[FeedbackResponse])
async def get_feedback(
    status: Optional[str] = None,
    feedback_type: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
) -> List[dict]:
    """
    Get feedback submissions.
    
    Regular users see only their own feedback.
    Admins see all feedback with optional filters.
    """
    supabase = get_supabase_client()
    
    # Build query
    query = supabase.table("feedback").select("*")
    
    # If not admin, filter to user's own feedback
    if current_user.get("role") != "admin":
        query = query.eq("user_id", current_user["id"])
    else:
        # Admin can filter by status and type
        if status:
            query = query.eq("status", status)
        if feedback_type:
            query = query.eq("feedback_type", feedback_type)
    
    # Order by created_at descending and limit
    query = query.order("created_at", desc=True).limit(limit)
    
    result = query.execute()
    return result.data


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(
    feedback_id: UUID,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get specific feedback by ID."""
    supabase = get_supabase_client()
    
    result = supabase.table("feedback").select("*").eq("id", str(feedback_id)).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    feedback = result.data[0]
    
    # Check permissions: user can see own feedback, admins can see all
    if feedback["user_id"] != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this feedback")
    
    return feedback


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    update: FeedbackUpdate,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Update feedback status, priority, or admin notes.
    
    Admin only.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    # Build update dict with only provided fields
    update_data = {}
    if update.status is not None:
        update_data["status"] = update.status
    if update.priority is not None:
        update_data["priority"] = update.priority
    if update.admin_notes is not None:
        update_data["admin_notes"] = update.admin_notes
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = supabase.table("feedback").update(update_data).eq("id", str(feedback_id)).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return result.data[0]


@router.get("/stats/summary")
async def get_feedback_stats(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get feedback statistics summary.
    
    Admin only - shows counts by status, type, and priority.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    supabase = get_supabase_client()
    
    # Get all feedback
    all_feedback = supabase.table("feedback").select("feedback_type, status, priority").execute()
    
    # Count by status
    status_counts = {}
    for fb in all_feedback.data:
        status = fb["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Count by type
    type_counts = {}
    for fb in all_feedback.data:
        fb_type = fb["feedback_type"]
        type_counts[fb_type] = type_counts.get(fb_type, 0) + 1
    
    # Count by priority
    priority_counts = {}
    for fb in all_feedback.data:
        priority = fb["priority"]
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    return {
        "total": len(all_feedback.data),
        "by_status": status_counts,
        "by_type": type_counts,
        "by_priority": priority_counts
    }
