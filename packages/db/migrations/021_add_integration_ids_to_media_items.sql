-- Migration 021: Add Integration IDs to Media Items
-- Purpose: Enable cascade deletion across Sonarr/Radarr/Overseerr
-- Adds foreign keys linking media items to external service IDs

-- Add integration ID columns to media_items
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS sonarr_series_id INTEGER,
ADD COLUMN IF NOT EXISTS radarr_movie_id INTEGER,
ADD COLUMN IF NOT EXISTS tmdb_id INTEGER,
ADD COLUMN IF NOT EXISTS tvdb_id INTEGER,
ADD COLUMN IF NOT EXISTS parent_title TEXT;

COMMENT ON COLUMN media_items.sonarr_series_id IS 'Sonarr series ID for TV shows - used for cascade deletion';
COMMENT ON COLUMN media_items.radarr_movie_id IS 'Radarr movie ID for movies - used for cascade deletion';
COMMENT ON COLUMN media_items.tmdb_id IS 'The Movie Database (TMDB) ID - universal identifier';
COMMENT ON COLUMN media_items.tvdb_id IS 'TheTVDB ID - used by Sonarr for TV shows';
COMMENT ON COLUMN media_items.parent_title IS 'Parent TV show title for episodes';

-- Create indexes for faster lookups during sync and deletion
CREATE INDEX IF NOT EXISTS idx_media_items_sonarr_series_id ON media_items(sonarr_series_id) WHERE sonarr_series_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_radarr_movie_id ON media_items(radarr_movie_id) WHERE radarr_movie_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_tmdb_id ON media_items(tmdb_id) WHERE tmdb_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_tvdb_id ON media_items(tvdb_id) WHERE tvdb_id IS NOT NULL;
