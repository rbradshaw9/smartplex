-- Migration: 010 - Add Overseerr User ID
-- Created: 2025-11-11
-- Description: Adds overseerr_user_id column to users table for request attribution

-- Add overseerr_user_id column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS overseerr_user_id INTEGER;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_overseerr_user_id 
ON users(overseerr_user_id) 
WHERE overseerr_user_id IS NOT NULL;

-- Add comment
COMMENT ON COLUMN users.overseerr_user_id IS 
'User ID in Overseerr system for attributing media requests';
