-- Migration: 011 - Add Genres Column to Media Items
-- Created: 2025-11-11
-- Description: Adds genres JSONB array column to media_items table for filtering and recommendations

-- Add genres column to media_items table
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS genres JSONB DEFAULT '[]'::jsonb;

-- Add index for genre filtering (GIN index for JSONB)
CREATE INDEX IF NOT EXISTS idx_media_items_genres 
ON media_items USING gin(genres);

-- Add comment
COMMENT ON COLUMN media_items.genres IS 
'Array of genre tags from Plex metadata (stored as JSONB for efficient querying)';
