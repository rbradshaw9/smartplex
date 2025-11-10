-- Migration: Add deletion_rules and deletion_history tables
-- Created: 2025-11-10
-- Description: Adds tables for intelligent library cleanup with grace periods and inactivity tracking

-- Deletion rules table (library cleanup configuration)
CREATE TABLE IF NOT EXISTS deletion_rules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  dry_run_mode BOOLEAN NOT NULL DEFAULT TRUE,
  grace_period_days INTEGER NOT NULL DEFAULT 30, -- Minimum days since added before considering for deletion
  inactivity_threshold_days INTEGER NOT NULL DEFAULT 15, -- Days without viewing to mark for deletion
  excluded_libraries JSONB DEFAULT '[]'::jsonb, -- Array of library IDs to skip
  excluded_genres JSONB DEFAULT '[]'::jsonb, -- Array of genre names to skip
  excluded_collections JSONB DEFAULT '[]'::jsonb, -- Array of collection names to skip
  min_rating DECIMAL(3,1), -- Only delete items below this rating (optional)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
  last_run_at TIMESTAMP WITH TIME ZONE,
  next_run_at TIMESTAMP WITH TIME ZONE,
  
  CONSTRAINT deletion_rules_grace_period_check CHECK (grace_period_days >= 0),
  CONSTRAINT deletion_rules_inactivity_check CHECK (inactivity_threshold_days >= 0),
  CONSTRAINT deletion_rules_rating_check CHECK (min_rating IS NULL OR (min_rating >= 0 AND min_rating <= 10))
);

-- Deletion history table (audit trail of all deletions)
CREATE TABLE IF NOT EXISTS deletion_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  rule_id UUID REFERENCES deletion_rules(id) ON DELETE SET NULL,
  media_item_id UUID REFERENCES media_items(id) ON DELETE SET NULL,
  plex_id TEXT NOT NULL,
  title TEXT NOT NULL,
  media_type media_type NOT NULL,
  date_added TIMESTAMP WITH TIME ZONE,
  last_viewed_at TIMESTAMP WITH TIME ZONE,
  view_count INTEGER DEFAULT 0,
  days_since_added INTEGER,
  days_since_viewed INTEGER,
  rating DECIMAL(3,1),
  file_size_mb BIGINT,
  deleted_from_plex BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_from_sonarr BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_from_radarr BOOLEAN NOT NULL DEFAULT FALSE,
  deletion_status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'skipped'
  error_message TEXT,
  dry_run BOOLEAN NOT NULL DEFAULT TRUE,
  deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  deleted_by UUID REFERENCES users(id) ON DELETE SET NULL,
  
  CONSTRAINT deletion_history_status_check CHECK (deletion_status IN ('pending', 'completed', 'failed', 'skipped'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_deletion_rules_enabled ON deletion_rules(enabled);
CREATE INDEX IF NOT EXISTS idx_deletion_rules_next_run_at ON deletion_rules(next_run_at);

CREATE INDEX IF NOT EXISTS idx_deletion_history_rule_id ON deletion_history(rule_id);
CREATE INDEX IF NOT EXISTS idx_deletion_history_media_item_id ON deletion_history(media_item_id);
CREATE INDEX IF NOT EXISTS idx_deletion_history_deleted_at ON deletion_history(deleted_at);
CREATE INDEX IF NOT EXISTS idx_deletion_history_deletion_status ON deletion_history(deletion_status);
CREATE INDEX IF NOT EXISTS idx_deletion_history_dry_run ON deletion_history(dry_run);

-- Update trigger for deletion_rules
CREATE TRIGGER update_deletion_rules_updated_at BEFORE UPDATE ON deletion_rules 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert a default deletion rule (disabled by default for safety)
INSERT INTO deletion_rules (
  name, 
  description, 
  enabled, 
  dry_run_mode,
  grace_period_days,
  inactivity_threshold_days
) VALUES (
  'Default Cleanup Rule',
  'Removes media that has not been watched in 15 days, but only if it was added more than 30 days ago',
  FALSE,
  TRUE,
  30,
  15
) ON CONFLICT DO NOTHING;
