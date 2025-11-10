-- Migration 007: AI Intelligence & Analytics
-- Adds columns and tables for Phase 5 AI features including admin analytics and self-learning

-- 13. Add user activity tracking for admin analytics
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- Create index for finding inactive users
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at DESC) WHERE last_login_at IS NOT NULL;

-- 14. Add request attribution (track WHO requested content for social analytics)
ALTER TABLE content_requests ADD COLUMN IF NOT EXISTS requested_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;

-- Backfill existing requests (set to the user_id who made them)
UPDATE content_requests SET requested_by_user_id = user_id WHERE requested_by_user_id IS NULL;

-- Create index for "whose requests get watched most" queries
CREATE INDEX IF NOT EXISTS idx_content_requests_requested_by ON content_requests(requested_by_user_id);

-- 15. Add social credit tracking (if a watch came from someone's request)
ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS attributed_to_request_id UUID REFERENCES content_requests(id) ON DELETE SET NULL;

-- Create index for social analytics
CREATE INDEX IF NOT EXISTS idx_user_stats_attributed_request ON user_stats(attributed_to_request_id) WHERE attributed_to_request_id IS NOT NULL;

-- 16. Add storage analytics for media items
ALTER TABLE media_items ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;

-- Create index for storage queries
CREATE INDEX IF NOT EXISTS idx_media_items_file_size ON media_items(file_size_bytes DESC) WHERE file_size_bytes IS NOT NULL;

-- 17. AI Conversation Feedback (AI self-learning system)
CREATE TABLE IF NOT EXISTS ai_conversation_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_history_id UUID REFERENCES chat_history(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_message TEXT NOT NULL,
  ai_response TEXT NOT NULL,
  
  -- AI self-assessment metrics
  confidence_score DECIMAL(3,2), -- 0.00 to 1.00 - AI's confidence in its answer
  data_sources_used JSONB DEFAULT '[]'::jsonb, -- Which tables/queries AI used
  missing_data JSONB DEFAULT '[]'::jsonb, -- What data AI wanted but didn't have
  
  -- User feedback (optional)
  user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5), -- 1-5 stars
  user_followed_up BOOLEAN DEFAULT FALSE, -- Did user ask clarifying question?
  user_reported_wrong BOOLEAN DEFAULT FALSE,
  
  -- Classification
  question_type TEXT, -- 'analytics', 'recommendation', 'troubleshooting', 'general'
  complexity TEXT CHECK (complexity IN ('simple', 'medium', 'complex')),
  was_successful BOOLEAN, -- AI's self-assessment
  requires_human_review BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT ai_feedback_confidence_check CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);

-- Indexes for AI feedback analysis
CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id ON ai_conversation_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_confidence ON ai_conversation_feedback(confidence_score) WHERE confidence_score < 0.7;
CREATE INDEX IF NOT EXISTS idx_ai_feedback_question_type ON ai_conversation_feedback(question_type);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_success ON ai_conversation_feedback(was_successful) WHERE was_successful = false;
CREATE INDEX IF NOT EXISTS idx_ai_feedback_created ON ai_conversation_feedback(created_at DESC);

-- 18. AI Learning Queue (track what AI can't answer well)
CREATE TABLE IF NOT EXISTS ai_learning_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  question TEXT NOT NULL,
  question_type TEXT, -- 'analytics', 'recommendation', 'feature_request', etc.
  
  -- Why it failed
  why_failed TEXT, -- 'missing_data', 'ambiguous_query', 'complex_calculation', 'unsupported_feature'
  missing_tables TEXT[], -- Which DB tables would help answer this
  missing_columns TEXT[], -- Which columns would help
  suggested_solution TEXT, -- AI's suggestion for how to fix this
  
  -- Tracking
  times_asked INTEGER DEFAULT 1, -- How many times this question came up
  priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 5), -- 1=low, 5=critical
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'wont_fix')),
  
  -- Resolution
  resolved_at TIMESTAMP WITH TIME ZONE,
  resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
  resolution_notes TEXT,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for learning queue
CREATE INDEX IF NOT EXISTS idx_ai_learning_status ON ai_learning_queue(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_ai_learning_priority ON ai_learning_queue(priority DESC, times_asked DESC);
CREATE INDEX IF NOT EXISTS idx_ai_learning_type ON ai_learning_queue(question_type);
CREATE INDEX IF NOT EXISTS idx_ai_learning_created ON ai_learning_queue(created_at DESC);

-- Trigger for ai_learning_queue updated_at
CREATE OR REPLACE FUNCTION update_ai_learning_queue_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_ai_learning_queue_updated_at
  BEFORE UPDATE ON ai_learning_queue
  FOR EACH ROW
  EXECUTE FUNCTION update_ai_learning_queue_updated_at();

-- 19. API Performance Logging (track AI costs and performance)
CREATE TABLE IF NOT EXISTS api_performance_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  
  -- Performance metrics
  status_code INTEGER,
  response_time_ms INTEGER,
  
  -- AI-specific metrics (when endpoint uses AI)
  ai_model TEXT, -- 'gpt-4o-mini', etc.
  ai_tokens_used INTEGER,
  ai_cost_estimate DECIMAL(10,6), -- Estimated cost in USD
  
  -- Error tracking
  error_message TEXT,
  error_type TEXT,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance analysis
CREATE INDEX IF NOT EXISTS idx_api_perf_endpoint ON api_performance_logs(endpoint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_perf_user ON api_performance_logs(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_perf_errors ON api_performance_logs(error_type, created_at DESC) WHERE error_message IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_perf_ai_costs ON api_performance_logs(created_at DESC) WHERE ai_tokens_used IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_perf_slow ON api_performance_logs(response_time_ms DESC) WHERE response_time_ms > 1000;

-- Comments for documentation
COMMENT ON COLUMN users.last_login_at IS 'Track user activity for admin analytics';
COMMENT ON COLUMN users.login_count IS 'Total number of logins for engagement tracking';
COMMENT ON COLUMN content_requests.requested_by_user_id IS 'Who made this request (for social credit analytics)';
COMMENT ON COLUMN user_stats.attributed_to_request_id IS 'If this watch was from someone else''s request (social influence tracking)';
COMMENT ON COLUMN media_items.file_size_bytes IS 'File size for storage analytics and cleanup decisions';
COMMENT ON TABLE ai_conversation_feedback IS 'AI tracks its own response quality and learns from mistakes';
COMMENT ON TABLE ai_learning_queue IS 'Questions AI struggled with - training queue for improvements';
COMMENT ON TABLE api_performance_logs IS 'API and AI performance tracking for cost control and optimization';
