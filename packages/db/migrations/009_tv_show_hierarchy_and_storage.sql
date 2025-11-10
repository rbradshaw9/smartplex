-- Migration: 009 - TV Show Hierarchy and Storage Configuration
-- Created: 2025-11-10
-- Description: Adds TV show hierarchy fields for aggregation and system config for manual storage capacity

-- ============================================
-- Part 1: TV Show Hierarchy Support
-- ============================================

-- Add hierarchy columns for TV shows/episodes
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS parent_title TEXT;

ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS grandparent_title TEXT;

ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS season_number INTEGER;

ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS episode_number INTEGER;

-- Add file_size_mb for easier queries (convert from file_size_bytes)
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS file_size_mb NUMERIC(10,2);

-- Populate file_size_mb from existing file_size_bytes
UPDATE media_items 
SET file_size_mb = ROUND((file_size_bytes / 1024.0 / 1024.0)::numeric, 2)
WHERE file_size_bytes IS NOT NULL AND file_size_mb IS NULL;

-- Add constraints
ALTER TABLE media_items 
ADD CONSTRAINT media_items_season_check 
CHECK (season_number IS NULL OR season_number >= 0);

ALTER TABLE media_items 
ADD CONSTRAINT media_items_episode_check 
CHECK (episode_number IS NULL OR episode_number >= 0);

ALTER TABLE media_items 
ADD CONSTRAINT media_items_file_size_mb_check 
CHECK (file_size_mb IS NULL OR file_size_mb >= 0);

-- Add indexes for fast aggregation queries
CREATE INDEX IF NOT EXISTS idx_media_items_grandparent_title 
ON media_items(grandparent_title) 
WHERE type = 'episode' AND grandparent_title IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_media_items_show_hierarchy 
ON media_items(grandparent_title, season_number, episode_number) 
WHERE type = 'episode';

CREATE INDEX IF NOT EXISTS idx_media_items_season 
ON media_items(grandparent_title, season_number) 
WHERE type = 'episode' AND grandparent_title IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_media_items_file_size_mb 
ON media_items(file_size_mb) 
WHERE file_size_mb IS NOT NULL;

-- Add comments
COMMENT ON COLUMN media_items.parent_title IS 
'Season title for episodes (e.g., "Season 1")';

COMMENT ON COLUMN media_items.grandparent_title IS 
'Show title for episodes (e.g., "Breaking Bad")';

COMMENT ON COLUMN media_items.season_number IS 
'Season number for episodes (1-based)';

COMMENT ON COLUMN media_items.episode_number IS 
'Episode number within season (1-based)';

COMMENT ON COLUMN media_items.file_size_mb IS 
'File size in megabytes (derived from file_size_bytes for easier queries)';

-- ============================================
-- Part 2: System Configuration Table
-- ============================================

-- Create system_config table for global settings
CREATE TABLE IF NOT EXISTS system_config (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
  
  CONSTRAINT system_config_key_check CHECK (char_length(key) >= 1)
);

-- Add trigger for updated_at
CREATE TRIGGER update_system_config_updated_at 
BEFORE UPDATE ON system_config 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add index
CREATE INDEX IF NOT EXISTS idx_system_config_updated_at 
ON system_config(updated_at);

-- Add comment
COMMENT ON TABLE system_config IS 
'Global system configuration settings (storage capacity, sync schedules, etc.)';

-- Insert default storage capacity (10TB default, users should update)
INSERT INTO system_config (key, value, description) VALUES 
(
  'storage_capacity', 
  '{"total_gb": 10000, "source": "manual", "notes": "Update this with your actual storage capacity"}'::jsonb,
  'Total storage capacity in GB for media library. Manually configured by admin.'
) ON CONFLICT (key) DO NOTHING;

-- ============================================
-- Part 3: SQL Functions for TV Show Aggregation
-- ============================================

-- Function to get unwatched shows aggregated from episodes
CREATE OR REPLACE FUNCTION get_unwatched_shows(
  days_since_added INTEGER DEFAULT 30,
  days_since_watched INTEGER DEFAULT 15
)
RETURNS TABLE (
  show_title TEXT,
  tvdb_id INTEGER,
  total_episodes BIGINT,
  total_size_gb NUMERIC,
  total_size_mb NUMERIC,
  last_watched_at TIMESTAMP WITH TIME ZONE,
  added_at TIMESTAMP WITH TIME ZONE,
  total_plays BIGINT,
  avg_play_count NUMERIC,
  days_since_last_watch INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    mi.grandparent_title AS show_title,
    MAX(mi.tvdb_id) AS tvdb_id,
    COUNT(*) AS total_episodes,
    ROUND(SUM(mi.file_size_mb) / 1024.0, 2) AS total_size_gb,
    ROUND(SUM(mi.file_size_mb), 2) AS total_size_mb,
    MAX(mi.last_watched_at) AS last_watched_at,
    MIN(mi.added_at) AS added_at,
    COALESCE(SUM(mi.total_play_count), 0) AS total_plays,
    ROUND(AVG(mi.total_play_count), 2) AS avg_play_count,
    EXTRACT(DAY FROM NOW() - MAX(COALESCE(mi.last_watched_at, mi.added_at)))::INTEGER AS days_since_last_watch
  FROM media_items mi
  WHERE mi.type = 'episode'
    AND mi.grandparent_title IS NOT NULL
  GROUP BY mi.grandparent_title
  HAVING 
    -- Grace period: added at least X days ago
    MIN(mi.added_at) < NOW() - (days_since_added || ' days')::INTERVAL
    -- Inactivity: not watched in X days (or never watched)
    AND (
      MAX(mi.last_watched_at) IS NULL 
      OR MAX(mi.last_watched_at) < NOW() - (days_since_watched || ' days')::INTERVAL
    )
  ORDER BY SUM(mi.file_size_mb) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get show statistics (for UI display)
CREATE OR REPLACE FUNCTION get_show_statistics(
  show_title_param TEXT
)
RETURNS TABLE (
  show_title TEXT,
  tvdb_id INTEGER,
  total_episodes BIGINT,
  total_seasons BIGINT,
  total_size_gb NUMERIC,
  total_plays BIGINT,
  last_watched_at TIMESTAMP WITH TIME ZONE,
  added_at TIMESTAMP WITH TIME ZONE,
  most_watched_episode TEXT,
  least_watched_season INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    mi.grandparent_title AS show_title,
    MAX(mi.tvdb_id) AS tvdb_id,
    COUNT(*) AS total_episodes,
    COUNT(DISTINCT mi.season_number) AS total_seasons,
    ROUND(SUM(mi.file_size_mb) / 1024.0, 2) AS total_size_gb,
    COALESCE(SUM(mi.total_play_count), 0) AS total_plays,
    MAX(mi.last_watched_at) AS last_watched_at,
    MIN(mi.added_at) AS added_at,
    (
      SELECT mi2.title 
      FROM media_items mi2 
      WHERE mi2.grandparent_title = mi.grandparent_title 
      ORDER BY mi2.total_play_count DESC NULLS LAST 
      LIMIT 1
    ) AS most_watched_episode,
    (
      SELECT mi3.season_number 
      FROM media_items mi3 
      WHERE mi3.grandparent_title = mi.grandparent_title 
      GROUP BY mi3.season_number 
      ORDER BY SUM(mi3.total_play_count) ASC NULLS FIRST 
      LIMIT 1
    ) AS least_watched_season
  FROM media_items mi
  WHERE mi.type = 'episode'
    AND mi.grandparent_title = show_title_param
  GROUP BY mi.grandparent_title;
END;
$$ LANGUAGE plpgsql;

-- Function to get season statistics for a show
CREATE OR REPLACE FUNCTION get_season_statistics(
  show_title_param TEXT
)
RETURNS TABLE (
  show_title TEXT,
  season_number INTEGER,
  episode_count BIGINT,
  total_size_gb NUMERIC,
  total_plays BIGINT,
  last_watched_at TIMESTAMP WITH TIME ZONE,
  avg_play_count NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    mi.grandparent_title AS show_title,
    mi.season_number,
    COUNT(*) AS episode_count,
    ROUND(SUM(mi.file_size_mb) / 1024.0, 2) AS total_size_gb,
    COALESCE(SUM(mi.total_play_count), 0) AS total_plays,
    MAX(mi.last_watched_at) AS last_watched_at,
    ROUND(AVG(mi.total_play_count), 2) AS avg_play_count
  FROM media_items mi
  WHERE mi.type = 'episode'
    AND mi.grandparent_title = show_title_param
    AND mi.season_number IS NOT NULL
  GROUP BY mi.grandparent_title, mi.season_number
  ORDER BY mi.season_number;
END;
$$ LANGUAGE plpgsql;

-- Add comments for functions
COMMENT ON FUNCTION get_unwatched_shows IS 
'Aggregates episodes by show to find unwatched or inactive shows for deletion candidates';

COMMENT ON FUNCTION get_show_statistics IS 
'Gets comprehensive statistics for a specific TV show including play counts and episode details';

COMMENT ON FUNCTION get_season_statistics IS 
'Gets statistics broken down by season for a specific TV show';
