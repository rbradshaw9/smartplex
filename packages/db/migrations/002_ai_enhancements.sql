-- AI Enhancements Migration
-- Adds tables and features for AI-powered recommendations and analysis

-- Create recommendations table to store AI-generated recommendations
CREATE TABLE IF NOT EXISTS recommendations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  media_item_id UUID REFERENCES media_items(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  media_type TEXT,
  reason TEXT NOT NULL,
  confidence REAL NOT NULL,
  imdb_id TEXT,
  tmdb_id INTEGER,
  year INTEGER,
  genres TEXT[],
  rating REAL,
  available_in_library BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE,
  viewed BOOLEAN DEFAULT FALSE,
  actioned BOOLEAN DEFAULT FALSE,
  
  CONSTRAINT recommendations_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT recommendations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10))
);

-- Create user preferences table for AI personalization
CREATE TABLE IF NOT EXISTS user_preferences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  favorite_genres TEXT[],
  disliked_genres TEXT[],
  preferred_decades INTEGER[],
  preferred_runtime_min INTEGER,
  preferred_runtime_max INTEGER,
  content_rating_preferences TEXT[],
  language_preferences TEXT[],
  ai_personality TEXT DEFAULT 'helpful', -- helpful, casual, concise, detailed
  recommendation_frequency TEXT DEFAULT 'normal', -- minimal, normal, frequent
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT user_prefs_runtime_check CHECK (
    (preferred_runtime_min IS NULL OR preferred_runtime_min >= 0) AND
    (preferred_runtime_max IS NULL OR preferred_runtime_max >= 0) AND
    (preferred_runtime_min IS NULL OR preferred_runtime_max IS NULL OR preferred_runtime_min <= preferred_runtime_max)
  )
);

-- Create embeddings table for semantic search (optional, for future)
CREATE TABLE IF NOT EXISTS media_embeddings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  media_item_id UUID NOT NULL REFERENCES media_items(id) ON DELETE CASCADE UNIQUE,
  embedding vector(1536), -- OpenAI ada-002 embedding size
  embedding_model TEXT NOT NULL DEFAULT 'text-embedding-ada-002',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create AI analysis cache to avoid re-analyzing same data
CREATE TABLE IF NOT EXISTS ai_analysis_cache (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  analysis_type TEXT NOT NULL, -- viewing_patterns, genre_analysis, etc
  time_period TEXT NOT NULL, -- 7d, 30d, 90d, 1y
  analysis_data JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  
  CONSTRAINT ai_cache_unique UNIQUE(user_id, analysis_type, time_period)
);

-- Indexes for performance
CREATE INDEX idx_recommendations_user_id ON recommendations(user_id);
CREATE INDEX idx_recommendations_created_at ON recommendations(created_at);
CREATE INDEX idx_recommendations_confidence ON recommendations(confidence DESC);
CREATE INDEX idx_recommendations_available ON recommendations(available_in_library);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

CREATE INDEX idx_ai_cache_user_id ON ai_analysis_cache(user_id);
CREATE INDEX idx_ai_cache_expires_at ON ai_analysis_cache(expires_at);

-- Add trigger for user_preferences updated_at
CREATE TRIGGER update_user_preferences_updated_at 
  BEFORE UPDATE ON user_preferences 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_media_embeddings_updated_at 
  BEFORE UPDATE ON media_embeddings 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- Add columns to chat_history for better AI context
ALTER TABLE chat_history 
  ADD COLUMN IF NOT EXISTS conversation_id UUID,
  ADD COLUMN IF NOT EXISTS sentiment TEXT,
  ADD COLUMN IF NOT EXISTS intent TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_chat_conversation_id ON chat_history(conversation_id);

-- Comments for documentation
COMMENT ON TABLE recommendations IS 'AI-generated content recommendations for users';
COMMENT ON TABLE user_preferences IS 'User preferences for AI personalization';
COMMENT ON TABLE media_embeddings IS 'Vector embeddings for semantic search (requires pgvector extension)';
COMMENT ON TABLE ai_analysis_cache IS 'Cached AI analysis results to reduce API costs';
