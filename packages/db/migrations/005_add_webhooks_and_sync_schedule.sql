-- Create webhook_log table to track all incoming webhooks
CREATE TABLE IF NOT EXISTS webhook_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  processed BOOLEAN DEFAULT FALSE,
  processed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT webhook_log_source_check CHECK (source IN ('plex', 'tautulli', 'sonarr', 'radarr', 'overseerr'))
);

-- Indexes for querying webhook history
CREATE INDEX IF NOT EXISTS idx_webhook_log_source ON webhook_log(source);
CREATE INDEX IF NOT EXISTS idx_webhook_log_event_type ON webhook_log(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_log_received_at ON webhook_log(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_log_processed ON webhook_log(processed);

-- Create sync_schedule table for configurable sync intervals
CREATE TABLE IF NOT EXISTS sync_schedule (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
  UNIQUE(service)
);

-- Insert default sync schedules
INSERT INTO sync_schedule (service, enabled, interval_hours) VALUES
  ('plex', true, 12),      -- Sync Plex library every 12 hours
  ('tautulli', true, 6),   -- Sync Tautulli stats every 6 hours
  ('sonarr', false, 24),   -- Optional: Sync Sonarr series every 24 hours
  ('radarr', false, 24),   -- Optional: Sync Radarr movies every 24 hours
  ('overseerr', false, 6)  -- Optional: Sync Overseerr requests every 6 hours
ON CONFLICT (service) DO NOTHING;

-- Create trigger to update updated_at
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

-- Add comments
COMMENT ON TABLE webhook_log IS 'Logs all incoming webhooks from Plex, Tautulli, Sonarr, Radarr, and Overseerr';
COMMENT ON TABLE sync_schedule IS 'Configurable sync schedules for each service with admin-adjustable intervals';

COMMENT ON COLUMN sync_schedule.interval_hours IS 'Hours between automatic syncs (1-168, i.e. 1 hour to 1 week)';
COMMENT ON COLUMN sync_schedule.last_run_at IS 'When the last sync completed';
COMMENT ON COLUMN sync_schedule.next_run_at IS 'When the next sync is scheduled';
