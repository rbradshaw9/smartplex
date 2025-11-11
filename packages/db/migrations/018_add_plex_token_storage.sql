-- Migration 018: Add Plex Token Storage
-- Purpose: Store encrypted Plex tokens per user for webhook support and per-user operations
-- Enables: Plex webhooks, per-user Plex API calls, better multi-user support

-- Add plex_token column to servers table (encrypted at application layer)
ALTER TABLE servers
ADD COLUMN IF NOT EXISTS plex_token TEXT;

COMMENT ON COLUMN servers.plex_token IS 'Encrypted Plex authentication token. Used for webhooks and per-user Plex API operations. Encrypted at application layer before storage.';

-- Create index for efficient token lookup (needed for webhook verification)
CREATE INDEX IF NOT EXISTS idx_servers_plex_token ON servers(plex_token) WHERE plex_token IS NOT NULL;

-- Add token metadata columns for management
ALTER TABLE servers
ADD COLUMN IF NOT EXISTS plex_token_expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS plex_token_last_validated_at TIMESTAMPTZ;

COMMENT ON COLUMN servers.plex_token_expires_at IS 'When the Plex token expires (if applicable). Used to prompt re-authentication.';
COMMENT ON COLUMN servers.plex_token_last_validated_at IS 'Last time token was successfully validated against Plex API. Used to detect revoked tokens.';

-- Create audit table for token operations (security best practice)
CREATE TABLE IF NOT EXISTS plex_token_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('stored', 'validated', 'revoked', 'expired', 'rotated')),
  ip_address TEXT,
  user_agent TEXT,
  success BOOLEAN NOT NULL DEFAULT true,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plex_token_audit_server_id ON plex_token_audit(server_id);
CREATE INDEX IF NOT EXISTS idx_plex_token_audit_user_id ON plex_token_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_plex_token_audit_created_at ON plex_token_audit(created_at DESC);

COMMENT ON TABLE plex_token_audit IS 'Audit log for Plex token operations. Tracks storage, validation, revocation for security monitoring.';

-- Enable RLS on audit table
ALTER TABLE plex_token_audit ENABLE ROW LEVEL SECURITY;

-- Users can only see their own token audit logs
CREATE POLICY "Users can view own token audit logs"
  ON plex_token_audit
  FOR SELECT
  USING (user_id = auth.uid());

-- Only authenticated users can create audit logs (via API)
CREATE POLICY "Authenticated users can create token audit logs"
  ON plex_token_audit
  FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL);
