-- Add Tautulli aggregated statistics to media_items table
-- These columns store server-wide metrics across ALL Plex users (not just SmartPlex users)
-- Data comes from Tautulli watch history API

-- Add total play count across all Plex users
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS total_play_count INTEGER DEFAULT 0;

-- Add last watched timestamp across all Plex users
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS last_watched_at TIMESTAMP WITH TIME ZONE;

-- Add total watch time in seconds across all Plex users
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS total_watch_time_seconds BIGINT DEFAULT 0;

-- Add Tautulli sync timestamp to track when stats were last updated
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS tautulli_synced_at TIMESTAMP WITH TIME ZONE;

-- Add constraints
ALTER TABLE media_items 
ADD CONSTRAINT media_items_total_play_count_check 
CHECK (total_play_count >= 0);

ALTER TABLE media_items 
ADD CONSTRAINT media_items_total_watch_time_check 
CHECK (total_watch_time_seconds >= 0);

-- Add indexes for deletion service queries
CREATE INDEX IF NOT EXISTS idx_media_items_total_play_count 
ON media_items(total_play_count);

CREATE INDEX IF NOT EXISTS idx_media_items_last_watched_at 
ON media_items(last_watched_at);

-- Add index for finding items that need Tautulli sync
CREATE INDEX IF NOT EXISTS idx_media_items_tautulli_sync 
ON media_items(tautulli_synced_at);

-- Add comments
COMMENT ON COLUMN media_items.total_play_count IS 
'Total number of plays across ALL Plex users (from Tautulli history)';

COMMENT ON COLUMN media_items.last_watched_at IS 
'Most recent watch timestamp across ALL Plex users (from Tautulli history)';

COMMENT ON COLUMN media_items.total_watch_time_seconds IS 
'Total watch time in seconds across ALL Plex users (from Tautulli history)';

COMMENT ON COLUMN media_items.tautulli_synced_at IS 
'Timestamp when Tautulli aggregated stats were last synced for this item';
