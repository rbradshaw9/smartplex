"""
AI and recommendation endpoints for SmartPlex API.
Handles chat interactions, content recommendations, and AI analysis.
"""

import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from app.core.supabase import get_supabase_client, get_current_user, get_optional_user
from app.core.exceptions import ValidationException, ExternalAPIException
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
        # Mock AI responses - in production, integrate with OpenAI/Anthropic
        mock_responses = [
            "Based on your recent viewing of action movies like 'The Batman', I recommend checking out 'Top Gun: Maverick' if it's available in your library. It has great reviews and fits your preference for high-quality action films.",
            
            "I noticed you've been watching a lot of superhero content lately. You might enjoy 'The Boys' series if you're looking for a darker take on the genre, or 'Invincible' for excellent animation.",
            
            "Your viewing statistics show you prefer content from the last 5 years. I can help you discover hidden gems in your library that match this preference. Would you like me to analyze your unwatched items?",
            
            "Looking at your watch history, you seem to enjoy both movies and series equally. For your next binge, consider 'House of the Dragon' if you like epic fantasy, or 'The Last of Us' for post-apocalyptic drama.",
            
            "I can help you optimize your library! Based on your viewing patterns, you might want to consider archiving content you haven't watched in over 6 months to free up space."
        ]
        
        # Select a relevant mock response
        response_text = random.choice(mock_responses)
        
        # Store chat interaction in database (mock)
        chat_record = {
            "user_id": current_user["id"],
            "message": chat_message.message,
            "response": response_text,
            "context": chat_message.context,
            "model_used": "gpt-3.5-turbo",  # Mock
            "tokens_used": 150,  # Mock
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # In production: supabase.table("chat_history").insert(chat_record).execute()
        
        return ChatResponse(
            response=response_text,
            context_used=bool(chat_message.context),
            tokens_used=150,
            model_used="gpt-3.5-turbo",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise ExternalAPIException(
            message="AI chat service unavailable",
            details=str(e)
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
        # Mock analysis - in production, analyze actual user data
        mock_analysis = {
            "summary": f"Over the past {analysis_request.time_period}, you've watched 47 items totaling 156 hours. Your viewing peaks on weekends, with a strong preference for action and sci-fi content released after 2020.",
            
            "insights": [
                "You watch 65% movies vs 35% TV series",
                "Action is your top genre (32% of viewing time)",
                "You prefer content with IMDB ratings above 7.0",
                "Weekend viewing is 3x higher than weekdays",
                "You rarely rewatch content (only 8% rewatches)"
            ],
            
            "recommendations": [
                {
                    "title": "Oppenheimer",
                    "type": "movie", 
                    "reason": "Highly rated recent drama matching your preference for quality content",
                    "confidence": 0.87
                },
                {
                    "title": "The Last of Us",
                    "type": "series",
                    "reason": "Post-apocalyptic series with excellent ratings and action elements",
                    "confidence": 0.82
                },
                {
                    "title": "Top Gun: Maverick", 
                    "type": "movie",
                    "reason": "Action-packed sequel to a classic, perfect for weekend viewing",
                    "confidence": 0.79
                }
            ] if analysis_request.include_recommendations else [],
            
            "statistics": {
                "total_items_watched": 47,
                "total_hours": 156,
                "average_rating": 7.8,
                "top_genre": "Action",
                "viewing_efficiency": "High",  # How much of started content is completed
                "discovery_rate": "Medium",   # How often user tries new content
            }
        }
        
        return AnalysisResponse(
            summary=mock_analysis["summary"],
            insights=mock_analysis["insights"],
            recommendations=mock_analysis["recommendations"],
            statistics=mock_analysis["statistics"],
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise ExternalAPIException(
            message="AI analysis service unavailable",
            details=str(e)
        )


@router.get("/recommendations")
async def get_recommendations(
    limit: int = Field(default=10, ge=1, le=100, description="Max 100 recommendations"),
    genre: Optional[str] = Field(default=None, max_length=50),
    content_type: Optional[str] = Field(default=None, pattern="^(movie|series)$"),  # movie, series, or None for both
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    supabase: Client = Depends(get_supabase_client)
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
        
    Returns:
        List of content recommendations with reasoning
    """
    try:
        # Mock recommendations - personalized if user is authenticated
        if current_user:
            # Personalized recommendations
            mock_recommendations = [
                {
                    "title": "Dune: Part Two",
                    "type": "movie",
                    "year": 2024,
                    "genre": ["Sci-Fi", "Adventure"],
                    "reason": "Sequel to 'Dune' which you rated highly",
                    "confidence": 0.92,
                    "imdb_rating": 8.8,
                    "available": True
                },
                {
                    "title": "The Bear",
                    "type": "series", 
                    "year": 2022,
                    "genre": ["Comedy", "Drama"],
                    "reason": "Critically acclaimed series perfect for your taste in character-driven content",
                    "confidence": 0.78,
                    "imdb_rating": 8.7,
                    "available": False
                }
            ]
        else:
            # General trending recommendations
            mock_recommendations = [
                {
                    "title": "Oppenheimer",
                    "type": "movie",
                    "year": 2023,
                    "genre": ["Biography", "Drama", "History"],
                    "reason": "Highly acclaimed biographical drama",
                    "confidence": 0.85,
                    "imdb_rating": 8.6,
                    "available": True
                },
                {
                    "title": "Wednesday",
                    "type": "series",
                    "year": 2022, 
                    "genre": ["Comedy", "Horror", "Mystery"],
                    "reason": "Popular supernatural comedy series",
                    "confidence": 0.80,
                    "imdb_rating": 8.2,
                    "available": True
                }
            ]
        
        # Apply filters
        if genre:
            mock_recommendations = [
                r for r in mock_recommendations 
                if genre.lower() in [g.lower() for g in r["genre"]]
            ]
            
        if content_type:
            mock_recommendations = [
                r for r in mock_recommendations
                if r["type"] == content_type
            ]
        
        return mock_recommendations[:limit]
        
    except Exception as e:
        raise ExternalAPIException(
            message="Recommendation service unavailable",
            details=str(e)
        )