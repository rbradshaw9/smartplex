-- Migration: 012 - Track Overseerr Requests
-- Created: 2025-11-11
-- Description: Adds table to track all Overseerr media requests made by users

-- Create overseerr_requests table
CREATE TABLE IF NOT EXISTS overseerr_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- User who made the request
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  overseerr_user_id INTEGER,
  
  -- Media details
  media_title TEXT NOT NULL,
  media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'tv')),
  tmdb_id INTEGER NOT NULL,
  tvdb_id INTEGER,
  seasons TEXT[], -- For TV shows, array of season numbers requested
  
  -- Overseerr details
  overseerr_request_id INTEGER, -- ID from Overseerr API
  overseerr_status TEXT, -- 'pending', 'approved', 'declined', 'available'
  
  -- Request metadata
  requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status_updated_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  
  -- Additional context
  notes TEXT,
  error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_overseerr_requests_user 
ON overseerr_requests(user_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_overseerr_requests_status 
ON overseerr_requests(overseerr_status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_overseerr_requests_tmdb 
ON overseerr_requests(tmdb_id);

CREATE INDEX IF NOT EXISTS idx_overseerr_requests_overseerr_id 
ON overseerr_requests(overseerr_request_id) 
WHERE overseerr_request_id IS NOT NULL;

-- Comments
COMMENT ON TABLE overseerr_requests IS 
'Tracks all media requests made through Overseerr integration for audit and history';

COMMENT ON COLUMN overseerr_requests.overseerr_status IS 
'Current status in Overseerr: pending (awaiting approval), approved (approved but not available), declined (rejected), available (downloaded and in library)';
