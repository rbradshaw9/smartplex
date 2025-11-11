-- Migration 014: Add Tautulli watch statistics to media_items
-- These fields store aggregated watch data from ALL Plex users (not just SmartPlex users)

ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS total_play_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_watched_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS total_watch_time_seconds INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS tautulli_synced_at TIMESTAMP WITH TIME ZONE;

-- Add indexes for deletion queries
CREATE INDEX IF NOT EXISTS idx_media_items_last_watched ON media_items(last_watched_at);
CREATE INDEX IF NOT EXISTS idx_media_items_play_count ON media_items(total_play_count);

-- Add comments
COMMENT ON COLUMN media_items.total_play_count IS 'Total play count across ALL Plex users (from Tautulli)';
COMMENT ON COLUMN media_items.last_watched_at IS 'Last watched timestamp across ALL Plex users (from Tautulli)';
COMMENT ON COLUMN media_items.total_watch_time_seconds IS 'Total watch time in seconds across ALL users (from Tautulli)';
COMMENT ON COLUMN media_items.tautulli_synced_at IS 'Timestamp of last Tautulli sync for this item';
