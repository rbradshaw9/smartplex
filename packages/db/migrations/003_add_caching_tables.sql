-- Add caching tables for improved performance
-- Run this in Supabase SQL editor

-- User statistics cache
CREATE TABLE IF NOT EXISTS user_stats_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    total_watched INTEGER DEFAULT 0,
    total_hours DECIMAL(10,2) DEFAULT 0,
    favorite_genre TEXT,
    stats_data JSONB DEFAULT '{}'::jsonb,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Watch history cache
CREATE TABLE IF NOT EXISTS watch_history_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plex_id TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    year INTEGER,
    duration INTEGER,
    last_viewed_at TIMESTAMPTZ,
    view_count INTEGER DEFAULT 0,
    rating DECIMAL(3,1),
    genres TEXT[],
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plex_id)
);

-- AI recommendations cache
CREATE TABLE IF NOT EXISTS recommendations_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    recommendations JSONB DEFAULT '[]'::jsonb,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_stats_cache_user_id ON user_stats_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_user_stats_cache_updated ON user_stats_cache(last_updated_at);
CREATE INDEX IF NOT EXISTS idx_watch_history_cache_user_id ON watch_history_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_history_cache_synced ON watch_history_cache(last_synced_at);
CREATE INDEX IF NOT EXISTS idx_recommendations_cache_user_id ON recommendations_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_cache_updated ON recommendations_cache(last_updated_at);

-- Enable RLS
ALTER TABLE user_stats_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE watch_history_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations_cache ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own stats cache"
    ON user_stats_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own stats cache"
    ON user_stats_cache FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own watch history cache"
    ON watch_history_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own watch history cache"
    ON watch_history_cache FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view own recommendations cache"
    ON recommendations_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own recommendations cache"
    ON recommendations_cache FOR ALL
    USING (auth.uid() = user_id);

COMMENT ON TABLE user_stats_cache IS 'Caches user Plex statistics for fast dashboard loading';
COMMENT ON TABLE watch_history_cache IS 'Caches watch history from Plex for quick access';
COMMENT ON TABLE recommendations_cache IS 'Caches AI recommendations to avoid recomputation';
