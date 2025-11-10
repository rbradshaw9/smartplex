-- Migration 008: Comprehensive Admin Activity Log
-- Central logging table for all administrative actions and system events

-- 20. Admin Activity Log (comprehensive system event tracking)
CREATE TABLE IF NOT EXISTS admin_activity_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Who/What
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  user_email TEXT,
  action_type TEXT NOT NULL, -- 'sync', 'deletion', 'user_action', 'system_event', 'config_change', 'integration', 'webhook'
  action TEXT NOT NULL, -- Specific action: 'plex_sync', 'tautulli_sync', 'media_deleted', 'user_created', etc.
  
  -- Context
  resource_type TEXT, -- 'media_item', 'user', 'server', 'integration', 'deletion_rule', etc.
  resource_id TEXT,
  resource_name TEXT, -- Human-readable name for quick reference
  
  -- Details
  details JSONB DEFAULT '{}'::jsonb, -- Flexible storage for action-specific data
  changes JSONB, -- Before/after for updates
  
  -- Results
  status TEXT NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'partial', 'failed', 'pending')),
  error_message TEXT,
  items_affected INTEGER DEFAULT 0, -- Count of items processed/changed
  
  -- Metadata
  ip_address TEXT,
  user_agent TEXT,
  duration_ms INTEGER, -- How long the operation took
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast filtering and searching
CREATE INDEX IF NOT EXISTS idx_admin_log_user ON admin_activity_log(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_admin_log_action_type ON admin_activity_log(action_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_log_action ON admin_activity_log(action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_log_resource ON admin_activity_log(resource_type, resource_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_log_status ON admin_activity_log(status, created_at DESC) WHERE status != 'success';
CREATE INDEX IF NOT EXISTS idx_admin_log_created ON admin_activity_log(created_at DESC);

-- Full text search on action and resource_name
CREATE INDEX IF NOT EXISTS idx_admin_log_search ON admin_activity_log USING gin(to_tsvector('english', action || ' ' || COALESCE(resource_name, '')));

-- 21. Sync Events Table (detailed sync tracking)
CREATE TABLE IF NOT EXISTS sync_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Sync details
  sync_type TEXT NOT NULL, -- 'plex', 'tautulli', 'sonarr', 'radarr', 'overseerr'
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  server_id UUID REFERENCES servers(id) ON DELETE SET NULL,
  integration_id UUID REFERENCES integrations(id) ON DELETE SET NULL,
  
  -- Trigger
  trigger_type TEXT NOT NULL, -- 'manual', 'scheduled', 'webhook', 'api'
  triggered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  
  -- Results
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
  items_discovered INTEGER DEFAULT 0,
  items_new INTEGER DEFAULT 0,
  items_updated INTEGER DEFAULT 0,
  items_removed INTEGER DEFAULT 0,
  items_failed INTEGER DEFAULT 0,
  
  -- Performance
  duration_ms INTEGER,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  
  -- Error tracking
  error_message TEXT,
  error_details JSONB,
  
  -- Metadata
  sync_metadata JSONB DEFAULT '{}'::jsonb -- Service-specific data
);

-- Indexes for sync event queries
CREATE INDEX IF NOT EXISTS idx_sync_events_user ON sync_events(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_type ON sync_events(sync_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_status ON sync_events(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_server ON sync_events(server_id, started_at DESC) WHERE server_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sync_events_running ON sync_events(started_at DESC) WHERE status = 'running';

-- 22. Deletion Events Table (comprehensive deletion tracking)
CREATE TABLE IF NOT EXISTS deletion_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- What was deleted
  media_item_id UUID, -- May be NULL if item already deleted
  plex_id TEXT NOT NULL,
  title TEXT NOT NULL,
  media_type TEXT,
  
  -- Why it was deleted
  deletion_rule_id UUID REFERENCES deletion_rules(id) ON DELETE SET NULL,
  deletion_reason TEXT, -- 'inactivity', 'low_rating', 'storage_limit', 'manual'
  deletion_score DECIMAL(5,2), -- Calculated score that triggered deletion
  
  -- Deletion details
  days_since_added INTEGER,
  days_since_viewed INTEGER,
  total_view_count INTEGER DEFAULT 0,
  file_size_mb BIGINT,
  
  -- Cascade tracking (deleted from all systems?)
  deleted_from_plex BOOLEAN DEFAULT FALSE,
  deleted_from_plex_at TIMESTAMP WITH TIME ZONE,
  deleted_from_sonarr BOOLEAN DEFAULT FALSE,
  deleted_from_sonarr_at TIMESTAMP WITH TIME ZONE,
  deleted_from_radarr BOOLEAN DEFAULT FALSE,
  deleted_from_radarr_at TIMESTAMP WITH TIME ZONE,
  deleted_from_overseerr BOOLEAN DEFAULT FALSE,
  deleted_from_overseerr_at TIMESTAMP WITH TIME ZONE,
  
  -- Status
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'partial', 'failed')),
  dry_run BOOLEAN NOT NULL DEFAULT TRUE,
  can_undo BOOLEAN DEFAULT FALSE,
  
  -- Who and when
  deleted_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Error tracking
  error_message TEXT,
  notes TEXT
);

-- Indexes for deletion tracking
CREATE INDEX IF NOT EXISTS idx_deletion_events_user ON deletion_events(deleted_by_user_id, deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_deletion_events_rule ON deletion_events(deletion_rule_id, deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_deletion_events_date ON deletion_events(deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_deletion_events_status ON deletion_events(status, deleted_at DESC) WHERE status != 'completed';
CREATE INDEX IF NOT EXISTS idx_deletion_events_dry_run ON deletion_events(dry_run, deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_deletion_events_title ON deletion_events(title);

-- Full text search on title
CREATE INDEX IF NOT EXISTS idx_deletion_events_search ON deletion_events USING gin(to_tsvector('english', title));

-- 23. Webhook Events Table (track all webhook activity)
CREATE TABLE IF NOT EXISTS webhook_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Source
  service TEXT NOT NULL, -- 'plex', 'tautulli', 'sonarr', 'radarr', 'overseerr'
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  server_id UUID REFERENCES servers(id) ON DELETE SET NULL,
  
  -- Event details
  event_type TEXT NOT NULL, -- 'library.new', 'media.play', 'media.scrobble', etc.
  payload JSONB NOT NULL, -- Full webhook payload
  
  -- Processing
  processed BOOLEAN DEFAULT FALSE,
  processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
  processing_started_at TIMESTAMP WITH TIME ZONE,
  processing_completed_at TIMESTAMP WITH TIME ZONE,
  processing_duration_ms INTEGER,
  
  -- Actions taken
  actions_triggered TEXT[], -- ['library_sync', 'metadata_update', etc.]
  sync_event_id UUID REFERENCES sync_events(id) ON DELETE SET NULL,
  
  -- Error tracking
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  
  -- Metadata
  ip_address TEXT,
  user_agent TEXT,
  received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for webhook tracking
CREATE INDEX IF NOT EXISTS idx_webhook_events_service ON webhook_events(service, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_events_user ON webhook_events(user_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_events_status ON webhook_events(processing_status, received_at DESC) WHERE processing_status != 'completed';
CREATE INDEX IF NOT EXISTS idx_webhook_events_pending ON webhook_events(received_at ASC) WHERE NOT processed;
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type ON webhook_events(event_type, received_at DESC);

-- Comments
COMMENT ON TABLE admin_activity_log IS 'Comprehensive log of all administrative actions and system events';
COMMENT ON TABLE sync_events IS 'Detailed tracking of all sync operations across services';
COMMENT ON TABLE deletion_events IS 'Complete audit trail of deletions with cascade tracking';
COMMENT ON TABLE webhook_events IS 'All incoming webhooks with processing status and results';

COMMENT ON COLUMN deletion_events.deleted_from_plex IS 'Whether item was successfully deleted from Plex';
COMMENT ON COLUMN deletion_events.deleted_from_sonarr IS 'Whether series was removed from Sonarr (prevents re-download)';
COMMENT ON COLUMN deletion_events.deleted_from_radarr IS 'Whether movie was removed from Radarr (prevents re-download)';
COMMENT ON COLUMN deletion_events.deleted_from_overseerr IS 'Whether request was removed from Overseerr (allows re-request)';
COMMENT ON COLUMN deletion_events.can_undo IS 'Whether deletion can be undone (file still exists but unlinked)';
