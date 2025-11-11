-- Migration 016: Add Watch List Table
-- Purpose: Allow users to save AI-recommended movies/shows to watch later
-- Solves: Bridge between AI recommendations and viewing decisions

-- Create watch_list table
CREATE TABLE IF NOT EXISTS watch_list (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- User who added this to their watch list
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Media item from Plex library (only items that exist in Plex)
  media_item_id UUID NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
  
  -- Priority/ranking (0-10, higher = more urgent to watch)
  priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 0 AND priority <= 10),
  
  -- Optional notes from user or AI recommendation context
  notes TEXT,
  
  -- Timestamps
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- User can only add same item once
  UNIQUE(user_id, media_item_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_watch_list_user ON watch_list(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_list_media ON watch_list(media_item_id);
CREATE INDEX IF NOT EXISTS idx_watch_list_priority ON watch_list(user_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_watch_list_added ON watch_list(user_id, added_at DESC);

-- Add comments
COMMENT ON TABLE watch_list IS 'User watch lists for AI-recommended content. Only stores items that exist in Plex library.';
COMMENT ON COLUMN watch_list.priority IS 'User priority ranking 0-10 (0=lowest, 10=highest). Used for sorting recommendations.';
COMMENT ON COLUMN watch_list.notes IS 'Optional context: why AI recommended this, user notes, or mood/genre tags.';

-- Create view for watch list with full media details
CREATE OR REPLACE VIEW watch_list_with_details AS
SELECT 
  wl.id,
  wl.user_id,
  wl.media_item_id,
  wl.priority,
  wl.notes,
  wl.added_at,
  mi.title,
  mi.type,
  mi.year,
  mi.tmdb_id,
  mi.imdb_id,
  mi.duration_ms,
  mi.metadata,
  mi.last_watched_at,
  mi.total_play_count,
  -- Calculate if never watched
  CASE WHEN mi.last_watched_at IS NULL THEN true ELSE false END as is_unwatched
FROM watch_list wl
JOIN media_items mi ON mi.id = wl.media_item_id
ORDER BY wl.priority DESC, wl.added_at DESC;

COMMENT ON VIEW watch_list_with_details IS 'Watch list joined with full media metadata for easy API queries.';
