-- Migration 006: Webhook Tenant Isolation + Phase 0 Critical Fixes
-- This migration adds user isolation for webhooks and fixes critical data integrity issues

-- 1. Add webhook authentication tokens to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_secret TEXT;

-- Generate unique webhook secrets for existing users
UPDATE users 
SET webhook_secret = encode(gen_random_bytes(32), 'hex')
WHERE webhook_secret IS NULL;

-- Make webhook_secret NOT NULL for future users
ALTER TABLE users ALTER COLUMN webhook_secret SET DEFAULT encode(gen_random_bytes(32), 'hex');

-- 2. Add user_id to webhook_log for proper tenant isolation
ALTER TABLE webhook_log ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE webhook_log ADD COLUMN IF NOT EXISTS server_id UUID REFERENCES servers(id) ON DELETE CASCADE;

-- Create index for filtering webhooks by user
CREATE INDEX IF NOT EXISTS idx_webhook_log_user_id ON webhook_log(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_log_server_id ON webhook_log(server_id);

-- 3. Add preferred_connection_url to servers table for Plex connection caching
ALTER TABLE servers ADD COLUMN IF NOT EXISTS preferred_connection_url TEXT;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS connection_tested_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS connection_latency_ms INTEGER;

-- 4. Fix integrations.server_id foreign key (it's currently TEXT, should be UUID FK)
-- First, check if the column exists and needs conversion
DO $$
BEGIN
    -- Only proceed if server_id column exists and is not already a proper FK
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'integrations' 
        AND column_name = 'server_id'
    ) THEN
        -- Drop the FK constraint if it exists
        ALTER TABLE integrations DROP CONSTRAINT IF EXISTS fk_integrations_server;
        
        -- Ensure server_id is UUID type (it should already be from schema.sql)
        -- This is safe if it's already UUID
        ALTER TABLE integrations ALTER COLUMN server_id TYPE UUID USING server_id::UUID;
        
        -- Add proper foreign key constraint
        ALTER TABLE integrations 
            ADD CONSTRAINT fk_integrations_server 
            FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 5. Fix NULL values in media_items that break recommendations
-- Add default values for scoring columns
ALTER TABLE media_items ALTER COLUMN year SET DEFAULT 0;
ALTER TABLE media_items ALTER COLUMN duration_ms SET DEFAULT 0;

-- Update existing NULL values
UPDATE media_items SET year = 0 WHERE year IS NULL;
UPDATE media_items SET duration_ms = 0 WHERE duration_ms IS NULL;

-- Fix NULL values in user_stats
UPDATE user_stats SET rating = 0.0 WHERE rating IS NULL;
UPDATE user_stats SET completion_percentage = 0.0 WHERE completion_percentage IS NULL;

-- 6. Add missing performance indexes
CREATE INDEX IF NOT EXISTS idx_media_items_tmdb_id ON media_items(tmdb_id) WHERE tmdb_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_tvdb_id ON media_items(tvdb_id) WHERE tvdb_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_imdb_id ON media_items(imdb_id) WHERE imdb_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(type);
CREATE INDEX IF NOT EXISTS idx_media_items_added_at ON media_items(added_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_items_server_type ON media_items(server_id, type);

-- Add compound index for user_stats queries
CREATE INDEX IF NOT EXISTS idx_user_stats_user_last_played ON user_stats(user_id, last_played_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_stats_user_play_count ON user_stats(user_id, play_count DESC);

-- 7. Add sync_schedule per user (not global)
-- Drop the global sync_schedule table and recreate with user_id
DROP TABLE IF EXISTS sync_schedule CASCADE;

CREATE TABLE sync_schedule (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  service TEXT NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  interval_hours INTEGER NOT NULL DEFAULT 6,
  last_run_at TIMESTAMP WITH TIME ZONE,
  next_run_at TIMESTAMP WITH TIME ZONE,
  run_count INTEGER DEFAULT 0,
  last_status TEXT,
  last_error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT sync_schedule_service_check CHECK (service IN ('plex', 'tautulli', 'sonarr', 'radarr', 'overseerr')),
  CONSTRAINT sync_schedule_interval_check CHECK (interval_hours >= 1 AND interval_hours <= 168),
  UNIQUE(user_id, service)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sync_schedule_user_id ON sync_schedule(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_schedule_next_run ON sync_schedule(next_run_at) WHERE enabled = true;

-- Recreate trigger
CREATE OR REPLACE FUNCTION update_sync_schedule_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sync_schedule_updated_at
  BEFORE UPDATE ON sync_schedule
  FOR EACH ROW
  EXECUTE FUNCTION update_sync_schedule_updated_at();

-- Insert default sync schedules for all existing users
INSERT INTO sync_schedule (user_id, service, enabled, interval_hours)
SELECT 
  u.id,
  s.service,
  s.enabled,
  s.interval_hours
FROM users u
CROSS JOIN (VALUES
  ('plex', true, 12),
  ('tautulli', true, 6),
  ('sonarr', false, 24),
  ('radarr', false, 24),
  ('overseerr', false, 6)
) AS s(service, enabled, interval_hours)
ON CONFLICT (user_id, service) DO NOTHING;

-- 8. Add content_requests table for tracking Overseerr requests
CREATE TABLE IF NOT EXISTS content_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'tv')),
  tmdb_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  year INTEGER,
  poster_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'available', 'declined', 'failed')),
  overseerr_request_id INTEGER,
  requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  approved_at TIMESTAMP WITH TIME ZONE,
  available_at TIMESTAMP WITH TIME ZONE,
  declined_at TIMESTAMP WITH TIME ZONE,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for content_requests
CREATE INDEX IF NOT EXISTS idx_content_requests_user_id ON content_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_content_requests_status ON content_requests(status);
CREATE INDEX IF NOT EXISTS idx_content_requests_tmdb_id ON content_requests(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_content_requests_requested_at ON content_requests(requested_at DESC);

-- Trigger for content_requests updated_at
CREATE OR REPLACE FUNCTION update_content_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_content_requests_updated_at
  BEFORE UPDATE ON content_requests
  FOR EACH ROW
  EXECUTE FUNCTION update_content_requests_updated_at();

-- 9. Add deletion_log table for audit trail
CREATE TABLE IF NOT EXISTS deletion_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  media_item_id UUID, -- Not FK since item will be deleted
  plex_id TEXT,
  title TEXT NOT NULL,
  type TEXT,
  year INTEGER,
  file_path TEXT,
  file_size_bytes BIGINT,
  deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  deleted_by UUID REFERENCES users(id) ON DELETE SET NULL,
  deletion_reason TEXT,
  deletion_score DECIMAL(5,2),
  last_watched_at TIMESTAMP WITH TIME ZONE,
  total_play_count INTEGER,
  can_undo BOOLEAN DEFAULT FALSE,
  notes TEXT
);

-- Indexes for deletion_log
CREATE INDEX IF NOT EXISTS idx_deletion_log_deleted_at ON deletion_log(deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_deletion_log_deleted_by ON deletion_log(deleted_by);
CREATE INDEX IF NOT EXISTS idx_deletion_log_title ON deletion_log(title);

-- Comments
COMMENT ON COLUMN users.webhook_secret IS 'Secret token for authenticating incoming webhooks';
COMMENT ON COLUMN servers.preferred_connection_url IS 'Cached URL that successfully connected to Plex (performance optimization)';
COMMENT ON COLUMN servers.connection_tested_at IS 'When the connection was last tested';
COMMENT ON COLUMN servers.connection_latency_ms IS 'Connection latency in milliseconds';
COMMENT ON COLUMN webhook_log.user_id IS 'User who owns the server that sent this webhook';
COMMENT ON COLUMN webhook_log.server_id IS 'Server that sent this webhook';
COMMENT ON TABLE sync_schedule IS 'Per-user configurable sync schedules for each service';
COMMENT ON TABLE content_requests IS 'User content requests made through Overseerr integration';
COMMENT ON TABLE deletion_log IS 'Audit log of all media deletions with reasons and scores';
