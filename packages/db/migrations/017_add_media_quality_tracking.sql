-- Migration 017: Add Media Quality Tracking
-- Purpose: Track video/audio quality for storage optimization insights
-- Enables: Codec analysis, resolution reporting, quality recommendations

-- Add quality and technical metadata columns to media_items
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS video_resolution TEXT,
ADD COLUMN IF NOT EXISTS video_codec TEXT,
ADD COLUMN IF NOT EXISTS audio_codec TEXT,
ADD COLUMN IF NOT EXISTS container TEXT,
ADD COLUMN IF NOT EXISTS bitrate_kbps INTEGER,
ADD COLUMN IF NOT EXISTS file_path TEXT,
ADD COLUMN IF NOT EXISTS accessible BOOLEAN DEFAULT true;

-- Create indexes for quality-based queries
CREATE INDEX IF NOT EXISTS idx_media_items_video_resolution ON media_items(video_resolution);
CREATE INDEX IF NOT EXISTS idx_media_items_video_codec ON media_items(video_codec);
CREATE INDEX IF NOT EXISTS idx_media_items_container ON media_items(container);
CREATE INDEX IF NOT EXISTS idx_media_items_accessible ON media_items(accessible) WHERE accessible = false;

-- Add comments
COMMENT ON COLUMN media_items.video_resolution IS 'Video resolution (e.g., "1080p", "4k", "720p"). Used for quality analysis and storage optimization.';
COMMENT ON COLUMN media_items.video_codec IS 'Video codec (e.g., "h264", "hevc", "av1"). Critical for identifying compression opportunities.';
COMMENT ON COLUMN media_items.audio_codec IS 'Audio codec (e.g., "aac", "dts", "truehd"). Useful for quality analysis.';
COMMENT ON COLUMN media_items.container IS 'Container format (e.g., "mkv", "mp4", "avi"). Helps identify remux candidates.';
COMMENT ON COLUMN media_items.bitrate_kbps IS 'Video bitrate in kbps. Higher bitrate = higher quality but more storage.';
COMMENT ON COLUMN media_items.file_path IS 'Full file path on server. Useful for troubleshooting and direct file operations.';
COMMENT ON COLUMN media_items.accessible IS 'Whether file is accessible on filesystem. False indicates broken/missing files.';

-- Create view for storage quality analysis
CREATE OR REPLACE VIEW storage_quality_analysis AS
SELECT 
  video_resolution,
  video_codec,
  container,
  COUNT(*) as item_count,
  SUM(file_size_bytes) as total_bytes,
  ROUND(SUM(file_size_bytes) / (1024.0 * 1024.0 * 1024.0), 2) as total_gb,
  ROUND(AVG(bitrate_kbps), 0) as avg_bitrate_kbps,
  ROUND(AVG(file_size_bytes / (1024.0 * 1024.0 * 1024.0)), 2) as avg_size_gb
FROM media_items
WHERE file_size_bytes IS NOT NULL
GROUP BY video_resolution, video_codec, container
ORDER BY total_bytes DESC;

COMMENT ON VIEW storage_quality_analysis IS 'Breakdown of storage by quality (resolution, codec, container). Shows optimization opportunities like H.264→HEVC conversions.';

-- Create view for broken/inaccessible files
CREATE OR REPLACE VIEW inaccessible_files AS
SELECT 
  id,
  title,
  type,
  file_path,
  file_size_bytes,
  ROUND(file_size_bytes / (1024.0 * 1024.0 * 1024.0), 2) as size_gb,
  added_at,
  updated_at
FROM media_items
WHERE accessible = false
ORDER BY file_size_bytes DESC NULLS LAST;

COMMENT ON VIEW inaccessible_files IS 'Lists broken or missing files. Helps identify storage issues and cleanup opportunities.';
