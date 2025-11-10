-- SmartPlex Database Schema
-- This file defines the complete database schema for SmartPlex
-- Run with: supabase db reset

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Custom types/enums
CREATE TYPE user_role AS ENUM ('admin', 'moderator', 'user', 'guest');
CREATE TYPE server_status AS ENUM ('online', 'offline', 'error');
CREATE TYPE integration_service AS ENUM ('tautulli', 'overseerr', 'sonarr', 'radarr', 'trakt', 'omdb');
CREATE TYPE integration_status AS ENUM ('active', 'inactive', 'error');
CREATE TYPE media_type AS ENUM ('movie', 'show', 'season', 'episode', 'track', 'album', 'artist');
CREATE TYPE cleanup_action AS ENUM ('deleted', 'quarantined', 'moved', 'analyzed');

-- Users table (extends Supabase auth.users)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT NOT NULL UNIQUE,
  display_name TEXT,
  avatar_url TEXT,
  role user_role NOT NULL DEFAULT 'user',
  plex_user_id TEXT,
  plex_username TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_active_at TIMESTAMP WITH TIME ZONE,
  preferences JSONB DEFAULT '{}'::jsonb,
  
  CONSTRAINT users_email_check CHECK (char_length(email) >= 3),
  CONSTRAINT users_display_name_check CHECK (char_length(display_name) >= 1)
);

-- Servers table (Plex servers)
CREATE TABLE servers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  machine_id TEXT,
  platform TEXT,
  version TEXT,
  status server_status NOT NULL DEFAULT 'offline',
  last_seen_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  config JSONB DEFAULT '{}'::jsonb,
  
  CONSTRAINT servers_name_check CHECK (char_length(name) >= 1),
  CONSTRAINT servers_url_check CHECK (url ~ '^https?://.*'),
  UNIQUE(user_id, machine_id)
);

-- Integrations table (external service connections)
CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
  service integration_service NOT NULL,
  name TEXT NOT NULL,
  url TEXT,
  api_key TEXT,
  config JSONB DEFAULT '{}'::jsonb,
  status integration_status NOT NULL DEFAULT 'inactive',
  last_sync_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT integrations_name_check CHECK (char_length(name) >= 1),
  UNIQUE(user_id, service, name)
);

-- Media items table (from Plex libraries)
CREATE TABLE media_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  plex_id TEXT NOT NULL,
  type media_type NOT NULL,
  title TEXT NOT NULL,
  year INTEGER,
  imdb_id TEXT,
  tmdb_id INTEGER,
  tvdb_id INTEGER,
  library_section TEXT,
  file_path TEXT,
  file_size_bytes BIGINT,
  duration_ms INTEGER,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb,
  
  CONSTRAINT media_items_title_check CHECK (char_length(title) >= 1),
  CONSTRAINT media_items_year_check CHECK (year IS NULL OR (year >= 1900 AND year <= 2100)),
  CONSTRAINT media_items_file_size_check CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
  CONSTRAINT media_items_duration_check CHECK (duration_ms IS NULL OR duration_ms >= 0),
  UNIQUE(server_id, plex_id)
);

-- User stats table (watch history and ratings)
CREATE TABLE user_stats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  media_item_id UUID NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
  play_count INTEGER NOT NULL DEFAULT 0,
  total_duration_ms BIGINT NOT NULL DEFAULT 0,
  last_played_at TIMESTAMP WITH TIME ZONE,
  completion_percentage REAL,
  rating REAL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT user_stats_play_count_check CHECK (play_count >= 0),
  CONSTRAINT user_stats_duration_check CHECK (total_duration_ms >= 0),
  CONSTRAINT user_stats_completion_check CHECK (completion_percentage IS NULL OR (completion_percentage >= 0 AND completion_percentage <= 100)),
  CONSTRAINT user_stats_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10)),
  UNIQUE(user_id, media_item_id)
);

-- Cleanup log table (track automated cleanup actions)
CREATE TABLE cleanup_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  media_item_id UUID REFERENCES media_items(id) ON DELETE SET NULL,
  action cleanup_action NOT NULL,
  file_path TEXT NOT NULL,
  file_size_bytes BIGINT,
  reason TEXT NOT NULL,
  performed_by TEXT, -- agent_id or user_id
  performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb,
  
  CONSTRAINT cleanup_log_file_path_check CHECK (char_length(file_path) >= 1),
  CONSTRAINT cleanup_log_reason_check CHECK (char_length(reason) >= 1),
  CONSTRAINT cleanup_log_file_size_check CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0)
);

-- Sync history table (track library synchronization)
CREATE TABLE sync_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  sync_type TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL,
  items_processed INTEGER NOT NULL DEFAULT 0,
  items_added INTEGER NOT NULL DEFAULT 0,
  items_updated INTEGER NOT NULL DEFAULT 0,
  items_removed INTEGER NOT NULL DEFAULT 0,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  
  CONSTRAINT sync_history_items_check CHECK (
    items_processed >= 0 AND 
    items_added >= 0 AND 
    items_updated >= 0 AND 
    items_removed >= 0
  )
);

-- Chat history table (AI conversations)
CREATE TABLE chat_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  response TEXT NOT NULL,
  context JSONB DEFAULT '{}'::jsonb,
  model_used TEXT,
  tokens_used INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT chat_history_message_check CHECK (char_length(message) >= 1),
  CONSTRAINT chat_history_response_check CHECK (char_length(response) >= 1),
  CONSTRAINT chat_history_tokens_check CHECK (tokens_used IS NULL OR tokens_used >= 0)
);

-- Agent heartbeats table (track agent status)
CREATE TABLE agent_heartbeats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id TEXT NOT NULL,
  server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'healthy',
  system_metrics JSONB DEFAULT '{}'::jsonb,
  last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT agent_heartbeats_agent_id_check CHECK (char_length(agent_id) >= 1)
);

-- Notifications table (in-app and external notifications)
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL, -- 'storage_alert', 'cleanup_complete', 'sync_error', 'recommendation', etc.
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info', -- 'info', 'warning', 'error', 'success'
  read BOOLEAN NOT NULL DEFAULT FALSE,
  data JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  read_at TIMESTAMP WITH TIME ZONE,
  
  CONSTRAINT notifications_type_check CHECK (char_length(type) >= 1),
  CONSTRAINT notifications_title_check CHECK (char_length(title) >= 1),
  CONSTRAINT notifications_message_check CHECK (char_length(message) >= 1),
  CONSTRAINT notifications_severity_check CHECK (severity IN ('info', 'warning', 'error', 'success'))
);

-- System settings table (global configuration)
CREATE TABLE system_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key TEXT NOT NULL UNIQUE,
  value JSONB NOT NULL,
  description TEXT,
  category TEXT NOT NULL, -- 'cache', 'cleanup', 'ai', 'notifications', 'integrations'
  is_secret BOOLEAN NOT NULL DEFAULT FALSE, -- whether value should be masked in UI
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
  
  CONSTRAINT system_settings_key_check CHECK (char_length(key) >= 1),
  CONSTRAINT system_settings_category_check CHECK (char_length(category) >= 1)
);

-- Audit log table (track admin actions)
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL, -- 'create', 'update', 'delete', 'login', 'execute_cleanup', etc.
  resource_type TEXT NOT NULL, -- 'integration', 'user', 'server', 'media_item', 'setting', etc.
  resource_id TEXT,
  changes JSONB DEFAULT '{}'::jsonb, -- before/after values
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT audit_log_action_check CHECK (char_length(action) >= 1),
  CONSTRAINT audit_log_resource_type_check CHECK (char_length(resource_type) >= 1)
);

-- Deletion rules table (library cleanup configuration)
CREATE TABLE deletion_rules (
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
CREATE TABLE deletion_history (
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
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_plex_user_id ON users(plex_user_id);
CREATE INDEX idx_users_created_at ON users(created_at);

CREATE INDEX idx_servers_user_id ON servers(user_id);
CREATE INDEX idx_servers_machine_id ON servers(machine_id);
CREATE INDEX idx_servers_status ON servers(status);

CREATE INDEX idx_integrations_user_id ON integrations(user_id);
CREATE INDEX idx_integrations_server_id ON integrations(server_id);
CREATE INDEX idx_integrations_service ON integrations(service);

CREATE INDEX idx_media_items_server_id ON media_items(server_id);
CREATE INDEX idx_media_items_plex_id ON media_items(plex_id);
CREATE INDEX idx_media_items_type ON media_items(type);
CREATE INDEX idx_media_items_title ON media_items(title);
CREATE INDEX idx_media_items_year ON media_items(year);
CREATE INDEX idx_media_items_imdb_id ON media_items(imdb_id);
CREATE INDEX idx_media_items_tmdb_id ON media_items(tmdb_id);

CREATE INDEX idx_user_stats_user_id ON user_stats(user_id);
CREATE INDEX idx_user_stats_media_item_id ON user_stats(media_item_id);
CREATE INDEX idx_user_stats_last_played ON user_stats(last_played_at);
CREATE INDEX idx_user_stats_play_count ON user_stats(play_count);

CREATE INDEX idx_cleanup_log_server_id ON cleanup_log(server_id);
CREATE INDEX idx_cleanup_log_performed_at ON cleanup_log(performed_at);
CREATE INDEX idx_cleanup_log_action ON cleanup_log(action);

CREATE INDEX idx_sync_history_user_id ON sync_history(user_id);
CREATE INDEX idx_sync_history_server_id ON sync_history(server_id);
CREATE INDEX idx_sync_history_started_at ON sync_history(started_at);

CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_history_created_at ON chat_history(created_at);

CREATE INDEX idx_agent_heartbeats_agent_id ON agent_heartbeats(agent_id);
CREATE INDEX idx_agent_heartbeats_last_heartbeat ON agent_heartbeats(last_heartbeat);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_type ON notifications(type);

CREATE INDEX idx_system_settings_key ON system_settings(key);
CREATE INDEX idx_system_settings_category ON system_settings(category);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource_type ON audit_log(resource_type);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

CREATE INDEX idx_deletion_rules_enabled ON deletion_rules(enabled);
CREATE INDEX idx_deletion_rules_next_run_at ON deletion_rules(next_run_at);

CREATE INDEX idx_deletion_history_rule_id ON deletion_history(rule_id);
CREATE INDEX idx_deletion_history_media_item_id ON deletion_history(media_item_id);
CREATE INDEX idx_deletion_history_deleted_at ON deletion_history(deleted_at);
CREATE INDEX idx_deletion_history_deletion_status ON deletion_history(deletion_status);
CREATE INDEX idx_deletion_history_dry_run ON deletion_history(dry_run);

-- Update triggers for timestamp fields
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_servers_updated_at BEFORE UPDATE ON servers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_integrations_updated_at BEFORE UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_media_items_updated_at BEFORE UPDATE ON media_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_stats_updated_at BEFORE UPDATE ON user_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deletion_rules_updated_at BEFORE UPDATE ON deletion_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();