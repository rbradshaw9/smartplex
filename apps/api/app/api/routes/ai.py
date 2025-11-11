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
        # Check if AI is configured
        if not settings.openai_api_key:
            # Fallback response when AI isn't configured
            return ChatResponse(
                response="🤖 AI chat is currently unavailable. The administrator needs to configure the AI service. In the meantime, you can explore your dashboard, browse recommendations, and request new content!",
                context_used=False,
                tokens_used=0,
                model_used="fallback",
                timestamp=datetime.utcnow()
            )
        
        # Initialize AI service
        ai_service = AIService(settings)
        
        # Get user's viewing context from database with full watch history
        user_stats = supabase.table('user_stats')\
            .select('*, media_items(*)')\
            .eq('user_id', current_user['id'])\
            .order('last_played_at', desc=True)\
            .limit(100)\
            .execute()
        
        # Build comprehensive user context with actual watch history
        recent_watches = []
        genre_counts = {}
        total_watch_count = 0
        
        if user_stats.data:
            for stat in user_stats.data:
                total_watch_count += stat.get('play_count', 0)
                if stat.get('media_items'):
                    media = stat['media_items']
                    
                    # Add to recent watches (last 10)
                    if len(recent_watches) < 10:
                        recent_watches.append({
                            "title": media.get('title'),
                            "type": media.get('type'),
                            "year": media.get('year'),
                            "rating": stat.get('rating'),
                            "play_count": stat.get('play_count', 0),
                            "last_played": stat.get('last_played_at')
                        })
                    
                    # Count genres for favorites
                    metadata = media.get('metadata', {})
                    genres = metadata.get('genres', [])
                    if isinstance(genres, list):
                        for genre in genres:
                            genre_counts[genre] = genre_counts.get(genre, 0) + stat.get('play_count', 1)
        
        # Get top 3 favorite genres
        favorite_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        favorite_genres = [genre for genre, _ in favorite_genres]
        
        # Calculate total watch time from media_items (if available from Tautulli sync)
        total_watch_hours = 0.0
        if user_stats.data:
            for stat in user_stats.data:
                if stat.get('media_items'):
                    media = stat['media_items']
                    # Get watch time from Tautulli sync data
                    watch_time_seconds = media.get('total_watch_time_seconds', 0)
                    if watch_time_seconds:
                        total_watch_hours += watch_time_seconds / 3600.0
        
        # Build enriched user context
        user_context = {
            "user_id": current_user["id"],
            "total_items_watched": len(user_stats.data) if user_stats.data else 0,
            "total_watch_count": total_watch_count,
            "total_watch_hours": round(total_watch_hours, 1),
            "favorite_genres": favorite_genres,
            "recent_watches": recent_watches,
            "viewing_summary": f"User has watched {len(user_stats.data)} different titles with {total_watch_count} total views ({total_watch_hours:.1f} hours total). Favorite genres: {', '.join(favorite_genres) if favorite_genres else 'none yet'}."
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
        
      # Get AI response with enriched user context
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


class RecommendationsRequest(BaseModel):
    """Request for AI recommendations."""
    user_id: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)
    genre: Optional[str] = None
    content_type: Optional[str] = None


@router.get("/recommendations")
@router.post("/recommendations")
async def get_recommendations(
    request: Optional[RecommendationsRequest] = None,
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
        # Use request body params if provided (POST), otherwise query params (GET)
        if request:
            limit = request.limit
            genre = request.genre
            content_type = request.content_type
        
        # Get recommendations - personalized if user is authenticated
        recommendations = []
        
        # If AI is configured, use it for personalized recommendations
        if settings.openai_api_key and current_user:
            try:
                ai_service = AIService(settings)
                # Get user's watch history for personalization
                user_stats = supabase.table('user_stats')\
                    .select('*, media_items(*)')\
                    .eq('user_id', current_user['id'])\
                    .order('last_played_at', desc=True)\
                    .limit(50)\
                    .execute()
                
                recent_watches = []
                liked_items = []
                disliked_items = []
                
                if user_stats.data:
                    for stat in user_stats.data:
                        if stat.get('media_items'):
                            media = stat['media_items']
                            item = {
                                "title": media.get('title'),
                                "type": media.get('type'),
                                "year": media.get('year') or 2023,  # Default to 2023 if None
                                "user_rating": stat.get('rating'),
                                "play_count": stat.get('play_count', 0)
                            }
                            recent_watches.append(item)
                            
                            # Categorize based on rating
                            rating = stat.get('rating')
                            if rating and rating >= 4:
                                liked_items.append(item)
                            elif rating and rating <= 2:
                                disliked_items.append(item)
                
                # Build user context dict
                user_context = {
                    "recent_watches": recent_watches,
                    "liked_items": liked_items,
                    "disliked_items": disliked_items,
                    "favorite_genres": []  # Could be derived from liked_items
                }
                
                # Get all media items in library to filter out
                media_items_result = supabase.table("media_items")\
                    .select("title, type, year, tmdb_id, imdb_id")\
                    .execute()
                
                existing_titles = set()
                existing_tmdb_ids = set()
                existing_imdb_ids = set()
                if media_items_result.data:
                    for item in media_items_result.data:
                        if item.get('title'):
                            existing_titles.add(item['title'].lower())
                        if item.get('tmdb_id'):
                            existing_tmdb_ids.add(str(item['tmdb_id']))
                        if item.get('imdb_id'):
                            existing_imdb_ids.add(str(item['imdb_id']))
                
                user_context["existing_library"] = {
                    "titles": list(existing_titles),
                    "tmdb_ids": list(existing_tmdb_ids),
                    "imdb_ids": list(existing_imdb_ids)
                }
                
                # Get AI recommendations based on history
                # Note: core/ai.py generate_recommendations expects (watch_history, available_content, limit)
                recommendations = await ai_service.generate_recommendations(
                    watch_history=recent_watches,  # First arg must be watch_history
                    available_content=None,  # We'll filter manually
                    limit=limit * 3  # Request more to account for filtering
                )
                
                # Filter out items already in library
                filtered_recommendations = []
                for rec in recommendations:
                    rec_title = rec.get('title', '').lower()
                    rec_tmdb = str(rec.get('tmdb_id', ''))
                    rec_imdb = str(rec.get('imdb_id', ''))
                    
                    # Skip if already in library
                    if rec_title in existing_titles:
                        continue
                    if rec_tmdb and rec_tmdb in existing_tmdb_ids:
                        continue
                    if rec_imdb and rec_imdb in existing_imdb_ids:
                        continue
                    
                    filtered_recommendations.append(rec)
                    if len(filtered_recommendations) >= limit:
                        break
                
                recommendations = filtered_recommendations
            except Exception as e:
                print(f"AI recommendations failed: {e}, falling back to generic")
                recommendations = []
        
        # Fallback to generic trending recommendations
        if not recommendations:
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
                },
                {
                    "title": "Succession",
                    "type": "series",
                    "year": 2023,
                    "reason": "Award-winning family drama",
                    "confidence": 0.88
                },
                {
                    "title": "The Bear",
                    "type": "series",
                    "year": 2023,
                    "reason": "Critically acclaimed restaurant drama",
                    "confidence": 0.84
                },
                {
                    "title": "Poor Things",
                    "type": "movie",
                    "year": 2023,
                    "reason": "Unique fantasy comedy-drama",
                    "confidence": 0.81
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