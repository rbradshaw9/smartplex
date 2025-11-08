"""
AI Service Module for SmartPlex
Handles OpenAI integration for chat, recommendations, and analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from openai import AsyncOpenAI
from app.config import Settings


class AIService:
    """Service for AI-powered features using OpenAI."""
    
    def __init__(self, settings: Settings):
        """Initialize AI service with OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4-turbo-preview"  # or gpt-3.5-turbo for cost savings
        
    async def chat(
        self,
        message: str,
        user_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Chat with AI assistant about media library.
        
        Args:
            message: User's message
            user_context: User's viewing history and preferences
            conversation_history: Previous messages in conversation
            
        Returns:
            AI response with tokens used and context
        """
        # Build system prompt with user context
        system_prompt = self._build_chat_system_prompt(user_context)
        
        # Prepare messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
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
            "model": self.model,
            "tokens_used": response.usage.total_tokens,
            "finish_reason": response.choices[0].finish_reason
        }
    
    async def generate_recommendations(
        self,
        user_context: Dict[str, Any],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized content recommendations.
        
        Args:
            user_context: User's viewing history and preferences
            count: Number of recommendations to generate
            
        Returns:
            List of recommendations with reasoning
        """
        system_prompt = """You are a media recommendation expert. 
        Analyze the user's viewing history and generate personalized recommendations.
        Return recommendations as JSON array with format:
        [{
          "title": "Movie/Show Title",
          "type": "movie" or "series",
          "year": 2024,
          "reason": "Why this is recommended",
          "confidence": 0.85,
          "genres": ["Action", "Sci-Fi"]
        }]
        """
        
        user_prompt = f"""Based on this viewing history, recommend {count} titles:

Recent watches: {json.dumps(user_context.get('recent_watches', [])[:10])}
Favorite genres: {user_context.get('favorite_genres', [])}
Highly rated by user: {json.dumps(user_context.get('liked_items', [])[:5])}
Disliked by user: {json.dumps(user_context.get('disliked_items', [])[:3])}

Provide diverse recommendations across different genres and types."""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        try:
            result = json.loads(response.choices[0].message.content)
            recommendations = result.get("recommendations", [])
            return recommendations[:count]
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return []
    
    async def analyze_viewing_patterns(
        self,
        watch_history: List[Dict[str, Any]],
        time_period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Analyze user's viewing patterns with AI insights.
        
        Args:
            watch_history: User's watch history data
            time_period: Time period for analysis
            
        Returns:
            Analysis with insights and statistics
        """
        system_prompt = """You are a data analyst specializing in media consumption patterns.
        Analyze the viewing history and provide insights about:
        - Viewing habits and patterns
        - Genre preferences
        - Content discovery behavior
        - Completion rates
        - Optimal viewing times
        
        Return analysis as JSON with:
        {
          "summary": "Overall analysis summary",
          "insights": ["Insight 1", "Insight 2", ...],
          "patterns": {"pattern_type": "description"},
          "recommendations": ["Suggestion 1", "Suggestion 2"]
        }
        """
        
        # Prepare viewing data for analysis
        analysis_data = {
            "total_items": len(watch_history),
            "time_period": time_period,
            "items": watch_history[:50],  # Limit to avoid token limits
        }
        
        user_prompt = f"Analyze this viewing data: {json.dumps(analysis_data)}"
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        try:
            analysis = json.loads(response.choices[0].message.content)
            return analysis
        except json.JSONDecodeError:
            return {
                "summary": "Analysis unavailable",
                "insights": [],
                "patterns": {},
                "recommendations": []
            }
    
    async def suggest_similar_content(
        self,
        title: str,
        media_type: str,
        available_library: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Suggest similar content from user's library.
        
        Args:
            title: Title user enjoyed
            media_type: Type of media (movie/series)
            available_library: User's available media items
            
        Returns:
            List of similar items from library
        """
        system_prompt = f"""You are a content similarity expert.
        Given a {media_type} title, find similar content from the provided library.
        Return top 5 most similar items with similarity reasoning."""
        
        user_prompt = f"""User enjoyed: "{title}"
        
Available in library:
{json.dumps(available_library[:100])}

Find similar titles and explain why they're similar."""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("similar_items", [])
        except json.JSONDecodeError:
            return []
    
    def _build_chat_system_prompt(self, user_context: Dict[str, Any]) -> str:
        """Build system prompt with user context."""
        prompt = """You are SmartPlex AI, an intelligent assistant for managing and discovering media content.

You help users with:
- Personalized content recommendations
- Library organization and analysis
- Finding what to watch next
- Understanding viewing habits
- Media discovery

Be conversational, helpful, and enthusiastic about media. Use the user's viewing history to provide personalized suggestions.
"""
        
        # Add user context
        if user_context:
            prompt += f"\n\nUser Context:"
            if user_context.get('favorite_genres'):
                prompt += f"\n- Favorite genres: {', '.join(user_context['favorite_genres'])}"
            if user_context.get('total_watched'):
                prompt += f"\n- Total items watched: {user_context['total_watched']}"
            if user_context.get('recent_watches'):
                recent = user_context['recent_watches'][:3]
                titles = [item.get('title') for item in recent]
                prompt += f"\n- Recently watched: {', '.join(titles)}"
        
        return prompt
