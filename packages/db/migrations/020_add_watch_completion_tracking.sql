-- Migration 020: Add Watch Completion Tracking
-- Purpose: Track partial vs complete views for smarter deletion decisions
-- Enables: Filter out partial plays, identify truly unwatched content

-- Add completion tracking columns to media_items
ALTER TABLE media_items
ADD COLUMN IF NOT EXISTS avg_percent_complete NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS complete_play_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS partial_play_count INTEGER DEFAULT 0;

COMMENT ON COLUMN media_items.avg_percent_complete IS 'Average percent of content watched across all plays (0-100). Used to identify content people start but don''t finish.';
COMMENT ON COLUMN media_items.complete_play_count IS 'Number of plays where >90% was watched. More accurate measure of actual views than total_play_count.';
COMMENT ON COLUMN media_items.partial_play_count IS 'Number of plays where <90% was watched. Indicates content people start but abandon.';

-- Create index for filtering by completion
CREATE INDEX IF NOT EXISTS idx_media_items_complete_play_count ON media_items(complete_play_count);

-- Add watch completion tracking to user_stats
ALTER TABLE user_stats
ADD COLUMN IF NOT EXISTS percent_complete NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS watched_status INTEGER DEFAULT 0;

COMMENT ON COLUMN user_stats.percent_complete IS 'Percent of content watched in this specific play session (0-100).';
COMMENT ON COLUMN user_stats.watched_status IS 'Tautulli watched status: 0 = unwatched, 1 = watched/completed.';

-- Create view for abandonded content (started but not finished)
CREATE OR REPLACE VIEW abandoned_content AS
SELECT 
  id,
  title,
  type,
  total_play_count,
  complete_play_count,
  partial_play_count,
  avg_percent_complete,
  file_size_bytes,
  ROUND(file_size_bytes / (1024.0 * 1024.0 * 1024.0), 2) as size_gb,
  last_watched_at,
  ROUND((partial_play_count::NUMERIC / NULLIF(total_play_count, 0)) * 100, 1) as abandonment_rate
FROM media_items
WHERE 
  total_play_count > 0
  AND complete_play_count = 0
  AND partial_play_count > 0
  AND avg_percent_complete < 50
ORDER BY file_size_bytes DESC NULLS LAST;

COMMENT ON VIEW abandoned_content IS 'Content that users started but never finished. High deletion candidates - taking up space with no engagement.';

-- Create view for low completion rate content
CREATE OR REPLACE VIEW low_completion_content AS
SELECT 
  id,
  title,
  type,
  total_play_count,
  complete_play_count,
  partial_play_count,
  avg_percent_complete,
  file_size_bytes,
  ROUND(file_size_bytes / (1024.0 * 1024.0 * 1024.0), 2) as size_gb,
  last_watched_at,
  ROUND((complete_play_count::NUMERIC / NULLIF(total_play_count, 0)) * 100, 1) as completion_rate
FROM media_items
WHERE 
  total_play_count >= 3
  AND (complete_play_count::NUMERIC / NULLIF(total_play_count, 0)) < 0.3
ORDER BY 
  file_size_bytes DESC NULLS LAST,
  completion_rate ASC;

COMMENT ON VIEW low_completion_content IS 'Content with low completion rate (<30%). Multiple people tried it but didn''t finish. Likely not engaging.';
