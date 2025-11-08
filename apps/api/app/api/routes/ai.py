"""
AI and recommendation endpoints for SmartPlex API.
Handles chat interactions, content recommendations, and AI analysis.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user, get_optional_user
from app.core.exceptions import ValidationException, ExternalAPIException
from app.core.ai import AIService
from app.config import get_settings, Settings

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message for AI conversation."""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    context: Optional[str] = Field(None, description="Additional context for AI")


class ChatResponse(BaseModel):
    """AI chat response."""
    response: str
    context_used: bool
    tokens_used: Optional[int] = None
    model_used: str
    timestamp: datetime


class AnalysisRequest(BaseModel):
    """Request for AI analysis of viewing patterns."""
    time_period: str = Field(default="30d", description="Analysis time period (7d, 30d, 90d, 1y)")
    include_recommendations: bool = Field(default=True, description="Include content recommendations")


class AnalysisResponse(BaseModel):
    """AI analysis response."""
    summary: str
    insights: List[str]
    recommendations: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    generated_at: datetime


@router.post("/chat")
async def chat_with_ai(
    chat_message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
) -> ChatResponse:
    """
    Chat with AI assistant about media library and recommendations.
    
    The AI can help with:
    - Content discovery and recommendations
    - Library analysis and insights
    - Viewing habit analysis
    - Content request suggestions
    
    Args:
        chat_message: User's chat message and optional context
        current_user: Authenticated user information
        supabase: Supabase client for database operations
        settings: Application settings
        
    Returns:
        AI response with recommendations and insights
    """
    try:
        # Initialize AI service
        ai_service = AIService(settings)
        
        # Get user's viewing context from database
        user_stats = supabase.table('user_stats').select('*').eq('user_id', current_user['id']).execute()
        
        # Build user context
        user_context = {
            "user_id": current_user["id"],
            "total_watched": len(user_stats.data) if user_stats.data else 0,
            "favorite_genres": [],  # TODO: Calculate from watch history
            "recent_watches": []  # TODO: Get from user_stats
        }
        
        # Get recent conversation history (last 5 messages)
        conversation_history = []
        recent_chats = supabase.table('chat_history')\
            .select('message, response')\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        if recent_chats.data:
            for chat in reversed(recent_chats.data):
                conversation_history.append({"role": "user", "content": chat['message']})
                conversation_history.append({"role": "assistant", "content": chat['response']})
        
        # Get AI response
        ai_response = await ai_service.chat(
            message=chat_message.message,
            user_context=user_context,
            conversation_history=conversation_history
        )
        
        # Store chat in database
        chat_record = {
            "user_id": current_user["id"],
            "message": chat_message.message,
            "response": ai_response["response"],
            "context": chat_message.context or {},
            "model_used": ai_response["model"],
            "tokens_used": ai_response["tokens_used"],
        }
        
        supabase.table("chat_history").insert(chat_record).execute()
        
        return ChatResponse(
            response=ai_response["response"],
            context_used=bool(chat_message.context),
            tokens_used=ai_response["tokens_used"],
            model_used=ai_response["model"],
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        print(f"AI chat error: {e}")
        raise ExternalAPIException(
            message="AI chat service unavailable",
            details=str(e) if settings.environment == "development" else None
        )


@router.post("/analyze")
async def analyze_viewing_patterns(
    analysis_request: AnalysisRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
) -> AnalysisResponse:
    """
    AI analysis of user viewing patterns and recommendations.
    
    Provides insights about:
    - Viewing habits and preferences
    - Genre distribution
    - Peak viewing times
    - Content recommendations
    - Library optimization suggestions
    
    Args:
        analysis_request: Analysis parameters and preferences
        current_user: Authenticated user information
        supabase: Supabase client for database operations
        settings: Application settings
        
    Returns:
        Comprehensive AI analysis and recommendations
    """
    try:
        # Initialize AI service
        ai_service = AIService(settings)
        
        # Get user's watch history from database
        user_stats = supabase.table('user_stats')\
            .select('*, media_items(*)')\
            .eq('user_id', current_user['id'])\
            .order('last_played_at', desc=True)\
            .limit(100)\
            .execute()
        
        # Build viewing data for AI analysis
        viewing_data = []
        if user_stats.data:
            for stat in user_stats.data:
                if stat.get('media_items'):
                    media = stat['media_items']
                    viewing_data.append({
                        "title": media.get('title'),
                        "type": media.get('type'),
                        "year": media.get('year'),
                        "play_count": stat.get('play_count', 0),
                        "last_played": stat.get('last_played_at'),
                        "rating": stat.get('rating'),
                        "metadata": media.get('metadata', {})
                    })
        
        # Get AI analysis
        ai_analysis = await ai_service.analyze_viewing_patterns(viewing_data, analysis_request.time_period)
        
        # Get recommendations if requested
        recommendations = []
        if analysis_request.include_recommendations:
            recommendations = await ai_service.generate_recommendations(viewing_data, limit=5)
        
        # Calculate basic statistics
        total_items = len(viewing_data)
        total_hours = sum(item.get('play_count', 1) * (item.get('duration', 0) / 1000 / 60 / 60) for item in viewing_data if item.get('duration'))
        
        rated_items = [item for item in viewing_data if item.get('rating')]
        avg_rating = sum(item['rating'] for item in rated_items) / len(rated_items) if rated_items else 0
        
        # Build statistics
        statistics = {
            "total_items_watched": total_items,
            "total_hours": round(total_hours, 1),
            "average_rating": round(avg_rating, 1) if avg_rating else None,
            "movies_vs_series": {
                "movies": sum(1 for item in viewing_data if item.get('type') == 'movie'),
                "series": sum(1 for item in viewing_data if item.get('type') in ['episode', 'show'])
            }
        }
        
        # Return AI-generated analysis
        return AnalysisResponse(
            summary=ai_analysis.get("summary", "No summary available"),
            insights=ai_analysis.get("insights", []),
            recommendations=recommendations,
            statistics=statistics,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise ExternalAPIException(
            message="AI analysis service unavailable",
            details=str(e)
        )


@router.get("/recommendations")
async def get_recommendations(
    limit: int = 10,
    genre: Optional[str] = None,
    content_type: Optional[str] = None,  # movie, series, or None for both
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    supabase: Client = Depends(get_supabase_client),
    settings: Settings = Depends(get_settings)
) -> List[Dict[str, Any]]:
    """
    Get AI-powered content recommendations.
    
    Can be used without authentication for general recommendations,
    or with authentication for personalized suggestions.
    
    Args:
        limit: Number of recommendations to return
        genre: Filter by specific genre
        content_type: Filter by movie or series
        current_user: Optional authenticated user for personalization
        supabase: Supabase client for database operations
        settings: Application settings
        
    Returns:
        List of content recommendations with reasoning
    """
    try:
        # Initialize AI service
        ai_service = AIService(settings)
        
        # Get recommendations - personalized if user is authenticated
        recommendations = []
        
        if current_user:
            # Get user's watch history for personalization
            user_stats = supabase.table('user_stats')\
                .select('*, media_items(*)')\
                .eq('user_id', current_user['id'])\
                .order('last_played_at', desc=True)\
                .limit(50)\
                .execute()
            
            viewing_data = []
            if user_stats.data:
                for stat in user_stats.data:
                    if stat.get('media_items'):
                        media = stat['media_items']
                        viewing_data.append({
                            "title": media.get('title'),
                            "type": media.get('type'),
                            "year": media.get('year'),
                            "user_rating": stat.get('rating'),
                            "play_count": stat.get('play_count', 0)
                        })
            
            # Get AI recommendations based on history
            recommendations = await ai_service.generate_recommendations(viewing_data, limit=limit)
        else:
            # Generic trending recommendations (could be cached)
            recommendations = [
                {
                    "title": "Oppenheimer",
                    "type": "movie",
                    "year": 2023,
                    "reason": "Highly acclaimed biographical drama",
                    "confidence": 0.85
                },
                {
                    "title": "The Last of Us",
                    "type": "series",
                    "year": 2023,
                    "reason": "Popular post-apocalyptic series",
                    "confidence": 0.82
                }
            ][:limit]
        
        # Apply filters
        if genre:
            recommendations = [
                r for r in recommendations 
                if genre.lower() in str(r.get("genre", "")).lower()
            ]
            
        if content_type:
            recommendations = [
                r for r in recommendations
                if r.get("type") == content_type
            ]
        
        return recommendations[:limit]
        
    except Exception as e:
        raise ExternalAPIException(
            message="Recommendation service unavailable",
            details=str(e)
        )