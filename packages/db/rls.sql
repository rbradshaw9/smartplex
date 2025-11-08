-- Row Level Security (RLS) Policies for SmartPlex
-- This file defines security policies to ensure users can only access their own data

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE cleanup_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_heartbeats ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can view their own profile" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON users
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Service role can manage users" ON users
  FOR ALL USING (auth.role() = 'service_role');

-- Servers table policies  
CREATE POLICY "Users can view their own servers" ON servers
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own servers" ON servers
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage servers" ON servers
  FOR ALL USING (auth.role() = 'service_role');

-- Integrations table policies
CREATE POLICY "Users can view their own integrations" ON integrations
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own integrations" ON integrations
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage integrations" ON integrations
  FOR ALL USING (auth.role() = 'service_role');

-- Media items table policies
CREATE POLICY "Users can view media from their servers" ON media_items
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM servers 
      WHERE servers.id = media_items.server_id 
      AND servers.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can manage media from their servers" ON media_items
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM servers 
      WHERE servers.id = media_items.server_id 
      AND servers.user_id = auth.uid()
    )
  );

CREATE POLICY "Service role can manage media items" ON media_items
  FOR ALL USING (auth.role() = 'service_role');

-- User stats table policies
CREATE POLICY "Users can view their own stats" ON user_stats
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own stats" ON user_stats
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage user stats" ON user_stats
  FOR ALL USING (auth.role() = 'service_role');

-- Cleanup log table policies
CREATE POLICY "Users can view cleanup logs from their servers" ON cleanup_log
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM servers 
      WHERE servers.id = cleanup_log.server_id 
      AND servers.user_id = auth.uid()
    )
  );

CREATE POLICY "Service role can manage cleanup logs" ON cleanup_log
  FOR ALL USING (auth.role() = 'service_role');

-- Sync history table policies
CREATE POLICY "Users can view their own sync history" ON sync_history
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own sync history" ON sync_history
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage sync history" ON sync_history
  FOR ALL USING (auth.role() = 'service_role');

-- Chat history table policies
CREATE POLICY "Users can view their own chat history" ON chat_history
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own chat history" ON chat_history
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage chat history" ON chat_history
  FOR ALL USING (auth.role() = 'service_role');

-- Agent heartbeats table policies
CREATE POLICY "Users can view heartbeats from their servers" ON agent_heartbeats
  FOR SELECT USING (
    server_id IS NULL OR
    EXISTS (
      SELECT 1 FROM servers 
      WHERE servers.id = agent_heartbeats.server_id 
      AND servers.user_id = auth.uid()
    )
  );

CREATE POLICY "Service role can manage agent heartbeats" ON agent_heartbeats
  FOR ALL USING (auth.role() = 'service_role');

-- Functions for common operations
CREATE OR REPLACE FUNCTION get_user_by_email(user_email TEXT)
RETURNS users AS $$
DECLARE
  user_record users%ROWTYPE;
BEGIN
  SELECT * INTO user_record FROM users WHERE email = user_email;
  RETURN user_record;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION create_user_profile(
  user_id UUID,
  user_email TEXT,
  display_name TEXT DEFAULT NULL,
  avatar_url TEXT DEFAULT NULL
)
RETURNS users AS $$
DECLARE
  new_user users%ROWTYPE;
BEGIN
  INSERT INTO users (id, email, display_name, avatar_url)
  VALUES (user_id, user_email, display_name, avatar_url)
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    display_name = COALESCE(EXCLUDED.display_name, users.display_name),
    avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
    updated_at = NOW()
  RETURNING * INTO new_user;
  
  RETURN new_user;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION update_user_last_active(user_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE users SET last_active_at = NOW() WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;