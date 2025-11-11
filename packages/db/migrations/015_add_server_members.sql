-- Migration 015: Add Server Members Table
-- Purpose: Track which users have access to which Plex servers
-- Solves: Multi-tenancy - users need to know which server's integrations to use

-- Create server_members table to track user access to servers
CREATE TABLE IF NOT EXISTS server_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- The server (owned by admin)
  server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  
  -- The user who has access (could be admin or regular user)
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- User's Plex username on this server
  plex_username TEXT,
  
  -- Role/permissions for this server
  role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('owner', 'admin', 'viewer')),
  
  -- Access status
  is_active BOOLEAN NOT NULL DEFAULT true,
  
  -- Timestamps
  joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_accessed_at TIMESTAMP WITH TIME ZONE,
  
  -- Prevent duplicate memberships
  UNIQUE(server_id, user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_server_members_server ON server_members(server_id);
CREATE INDEX IF NOT EXISTS idx_server_members_user ON server_members(user_id);
CREATE INDEX IF NOT EXISTS idx_server_members_active ON server_members(server_id, is_active) WHERE is_active = true;

-- Add comments
COMMENT ON TABLE server_members IS 'Tracks which users have access to which Plex servers. Used to determine which integrations a user can use.';
COMMENT ON COLUMN server_members.role IS 'User role for this server: owner (created server), admin (can manage), viewer (read-only)';
COMMENT ON COLUMN server_members.plex_username IS 'User''s Plex username on this specific server (may differ from SmartPlex display name)';
COMMENT ON COLUMN server_members.is_active IS 'Whether user currently has access (can be revoked by server owner)';

-- Automatically add server owner as member when server is created
-- This ensures the admin who creates a server is automatically a member
CREATE OR REPLACE FUNCTION add_server_owner_as_member()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO server_members (server_id, user_id, role, is_active)
  VALUES (NEW.id, NEW.user_id, 'owner', true)
  ON CONFLICT (server_id, user_id) DO NOTHING;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_add_server_owner
  AFTER INSERT ON servers
  FOR EACH ROW
  EXECUTE FUNCTION add_server_owner_as_member();

-- Backfill existing servers: add current owners as members
INSERT INTO server_members (server_id, user_id, role, is_active)
SELECT id, user_id, 'owner', true
FROM servers
ON CONFLICT (server_id, user_id) DO NOTHING;
