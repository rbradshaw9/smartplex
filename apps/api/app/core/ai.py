"""
AI service for SmartPlex using OpenAI GPT models.
Handles chat, recommendations, and content analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from openai import AsyncOpenAI
from supabase import Client

from app.config import Settings


class AIService:
    """Service for AI-powered features using OpenAI."""
    
    def __init__(self, settings: Settings):
        """Initialize AI service with OpenAI client."""
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective
        
    async def chat(
        self,
        message: str,
        user_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Chat with AI about media library and recommendations.
        
        Args:
            message: User's message
            user_context: Context about user's viewing habits, library, etc.
            chat_history: Previous conversation for context
            
        Returns:
            Dict with response, tokens used, and model info
        """
        # Build system prompt with context
        system_prompt = self._build_system_prompt(user_context)
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history if provided
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": "user" if msg.get("is_user") else "assistant",
                    "content": msg.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "response": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": self.model,
            "timestamp": datetime.utcnow()
        }
    
    async def analyze_viewing_patterns(
        self,
        watch_history: List[Dict[str, Any]],
        time_period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Analyze user's viewing patterns using AI.
        
        Args:
            watch_history: List of watched items with metadata
            time_period: Analysis period (7d, 30d, 90d, 1y)
            
        Returns:
            Analysis with insights and statistics
        """
        # Prepare viewing data summary for AI
        summary = self._summarize_watch_history(watch_history)
        
        prompt = f"""Analyze this viewing data for the past {time_period}:

{summary}

Provide:
1. A 2-sentence summary of viewing habits
2. 3-5 key insights about preferences and patterns
3. Notable trends or changes

Format as JSON with keys: summary, insights (array), trends (array)"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a media consumption analyst. Provide concise, actionable insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        analysis = json.loads(response.choices[0].message.content)
        
        return {
            **analysis,
            "tokens_used": response.usage.total_tokens,
            "generated_at": datetime.utcnow()
        }
    
    async def generate_recommendations(
        self,
        watch_history: List[Dict[str, Any]],
        available_content: Optional[List[Dict[str, Any]]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized content recommendations.
        
        Args:
            watch_history: User's watch history with ratings
            available_content: Content available in user's library
            limit: Number of recommendations to generate
            
        Returns:
            List of recommendations with reasoning
        """
        # Build context about user preferences
        liked_items = [item for item in watch_history if item.get("user_rating", 0) >= 7]
        recently_watched = watch_history[:20]
        
        # Build prompt
        liked_titles = [f"{item['title']} ({item.get('year', 'N/A')})" for item in liked_items[:10]]
        recent_titles = [f"{item['title']} ({item.get('type', 'N/A')})" for item in recently_watched[:10]]
        
        prompt = f"""Based on this viewing profile:

Recently Watched:
{chr(10).join('- ' + t for t in recent_titles)}

Highly Rated:
{chr(10).join('- ' + t for t in liked_titles)}

Recommend {limit} movies or TV shows they would enjoy. For each:
- Explain why it matches their taste
- Rate confidence (0-1)

Format as JSON array with: title, type, year, reason, confidence"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a personalized content recommendation engine. Suggest diverse, high-quality content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        # Parse recommendations
        result = json.loads(response.choices[0].message.content)
        recommendations = result.get("recommendations", [])
        
        # Match with available content if provided
        if available_content:
            recommendations = self._match_available_content(recommendations, available_content)
        
        return recommendations[:limit]
    
    def _build_system_prompt(self, user_context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt with user context."""
        base_prompt = """You are SmartPlex AI, an intelligent assistant for a Plex media server.

You help users:
- Discover content in their library
- Get personalized recommendations
- Analyze viewing habits
- Optimize their media collection

Be conversational, helpful, and concise. Reference specific titles when relevant."""
        
        if not user_context:
            return base_prompt
        
        # Add context about user's library and preferences
        context_additions = []
        
        if user_context.get("favorite_genre"):
            context_additions.append(f"User's favorite genre: {user_context['favorite_genre']}")
        
        if user_context.get("total_watched"):
            context_additions.append(f"Total items watched: {user_context['total_watched']}")
        
        if user_context.get("recently_watched"):
            recent = user_context["recently_watched"][:5]
            titles = [item.get("title") for item in recent]
            context_additions.append(f"Recently watched: {', '.join(titles)}")
        
        if context_additions:
            return f"{base_prompt}\n\nCurrent user context:\n" + "\n".join(f"- {c}" for c in context_additions)
        
        return base_prompt
    
    def _summarize_watch_history(self, watch_history: List[Dict[str, Any]]) -> str:
        """Summarize watch history for AI analysis."""
        if not watch_history:
            return "No viewing data available."
        
        # Calculate stats
        total_items = len(watch_history)
        total_duration = sum(item.get("duration", 0) for item in watch_history) / 1000 / 60 / 60  # Convert to hours
        
        # Genre distribution
        genres: Dict[str, int] = {}
        for item in watch_history:
            for genre in item.get("genres", []):
                genres[genre] = genres.get(genre, 0) + 1
        
        top_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Content types
        movies = sum(1 for item in watch_history if item.get("type") == "movie")
        series = sum(1 for item in watch_history if item.get("type") == "episode")
        
        summary = f"""Total Items: {total_items}
Total Hours: {total_duration:.1f}
Content Mix: {movies} movies, {series} episodes
Top Genres: {', '.join(f'{g[0]} ({g[1]})' for g in top_genres)}
Average Rating: {sum(item.get('rating', 0) for item in watch_history if item.get('rating')) / len([i for i in watch_history if i.get('rating')]) if any(i.get('rating') for i in watch_history) else 'N/A'}"""
        
        return summary
    
    def _match_available_content(
        self,
        recommendations: List[Dict[str, Any]],
        available_content: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Match recommendations with available content in library."""
        # Simple title matching - can be improved with fuzzy matching
        available_titles = {item.get("title", "").lower() for item in available_content}
        
        for rec in recommendations:
            rec_title = rec.get("title", "").lower()
            rec["available"] = rec_title in available_titles
        
        return recommendations


async def get_ai_service(settings: Settings) -> AIService:
    """Dependency for getting AI service."""
    return AIService(settings)
