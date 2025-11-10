# AI Capabilities Specification

## User-Level Questions (Current Implementation)

### Content Discovery
✅ **Currently Supported:**
- "What should I watch tonight?" → Uses watch history + ratings
- "Recommend something like [movie/show]" → Genre/style matching
- "What are my most watched genres?" → Stats from user_stats
- "Show me highly rated movies I haven't watched" → Available via media_items

❌ **Missing Data/Context:**
- "What's new in my library this week?" → Need `media_items.added_at` filtering
- "What are other users watching?" → Need cross-user stats (privacy considerations)
- "What's trending on my server?" → Need aggregate view_count across users
- "What unwatched content do I have?" → Need JOIN to find media_items NOT IN user_stats

### Personal Analytics
✅ **Currently Supported:**
- "How much have I watched this month?" → user_stats timestamps
- "What's my average rating?" → user_stats.rating
- "Show my watch history" → user_stats + media_items

❌ **Missing Data/Context:**
- "When do I watch the most?" → Need hour-of-day from user_stats.last_played_at
- "How long until I finish this series?" → Need episodes remaining calculation
- "What did I watch last Christmas?" → Need date range queries
- "Which shows have I abandoned?" → Need partial completion detection

### Request Management
✅ **Currently Supported:**
- "What did I request?" → content_requests table

❌ **Missing Data/Context:**
- "How long do requests usually take?" → Need avg(available_at - requested_at)
- "Who approves requests fastest?" → Need admin response time tracking
- "What requests have been declined?" → Need decline reason logging

---

## Admin-Level Questions (NEW REQUIREMENT)

### User Analytics
**High Value Questions:**
- "Which users are most active?" → Need user_stats aggregation
- "Who hasn't logged in recently?" → Need users.last_login_at (MISSING COLUMN!)
- "Which users watch the most content?" → SUM(play_count) by user_id
- "Who rates content the most?" → COUNT(ratings) by user_id
- "Which users request the most content?" → COUNT(content_requests) by user_id
- "Who watches requested content?" → Need content_requests → media_items → user_stats chain

**Social/Influence Questions:**
- "Whose requests get watched the most by others?" → CRITICAL: Need request_made_by tracking!
- "Which users discover content others love?" → Need request attribution + ratings from others
- "Who are the power users?" → Multi-metric scoring
- "Which users never watch what they request?" → Request vs watch correlation

### Content Analytics
- "What content is most popular across all users?" → SUM(play_count) GROUP BY media_item_id
- "What genres are most watched server-wide?" → Genre aggregation
- "What content is never watched?" → media_items with no user_stats
- "What content should I remove?" → Low play_count + old added_at
- "What's the storage usage by library?" → Need file_size tracking (MISSING!)

### System Health
- "Are there any sync errors?" → sync_schedule.last_error
- "When was the last successful Plex sync?" → sync_schedule.last_run_at
- "Which integrations are failing?" → Need integration health tracking
- "How many webhooks today?" → webhook_log COUNT by date
- "What's the API error rate?" → Need API logging (MISSING!)

### Operational Insights
- "How much bandwidth are we using?" → Need bandwidth tracking (MISSING!)
- "What's the average request approval time?" → content_requests timing
- "How many deletions this month?" → deletion_log aggregation
- "What's the library growth rate?" → media_items added_at trends

---

## Database Schema Gaps

### CRITICAL Missing Columns:
```sql
-- Track who made content requests (for social analytics)
ALTER TABLE content_requests ADD COLUMN requested_by_user_id UUID REFERENCES users(id);

-- Track user login activity
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;

-- Track media file sizes for storage analytics
ALTER TABLE media_items ADD COLUMN file_size_bytes BIGINT;

-- Track who attributed a watch (if from someone else's request)
ALTER TABLE user_stats ADD COLUMN attributed_to_request_id UUID REFERENCES content_requests(id);
```

### Nice-to-Have Analytics Tables:
```sql
-- API request logging for health monitoring
CREATE TABLE api_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER,
  response_time_ms INTEGER,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bandwidth tracking
CREATE TABLE bandwidth_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  media_item_id UUID REFERENCES media_items(id),
  bytes_transferred BIGINT,
  stream_duration_seconds INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## AI Self-Learning System (INNOVATIVE!)

### Architecture: AI Confidence Tracking

```sql
-- Track AI responses and their effectiveness
CREATE TABLE ai_conversation_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_history_id UUID REFERENCES chat_history(id),
  user_id UUID REFERENCES users(id),
  user_message TEXT NOT NULL,
  ai_response TEXT NOT NULL,
  
  -- AI self-assessment
  confidence_score DECIMAL(3,2), -- 0.00 to 1.00
  data_sources_used JSONB, -- Which tables/queries were used
  missing_data JSONB, -- What data AI wanted but couldn't access
  
  -- User feedback
  user_rating INTEGER, -- 1-5 stars (optional)
  user_followed_up BOOLEAN DEFAULT FALSE, -- Did user ask clarifying question?
  user_reported_wrong BOOLEAN DEFAULT FALSE,
  
  -- Learning signals
  question_type TEXT, -- 'analytics', 'recommendation', 'troubleshooting', etc.
  complexity TEXT, -- 'simple', 'medium', 'complex'
  was_successful BOOLEAN, -- AI's self-assessment
  requires_human_review BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track what AI couldn't answer (training queue)
CREATE TABLE ai_learning_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  question TEXT NOT NULL,
  question_type TEXT,
  why_failed TEXT, -- 'missing_data', 'ambiguous_query', 'complex_calculation', etc.
  missing_tables TEXT[], -- Which tables/columns would help
  suggested_solution TEXT, -- AI's suggestion for how to fix
  priority INTEGER DEFAULT 1, -- 1-5, higher = more important
  times_asked INTEGER DEFAULT 1, -- Increment when same question asked again
  status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'resolved', 'wont_fix'
  resolved_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Implementation Strategy:

1. **AI Response Wrapper** (in `core/ai.py`):
```python
async def chat_with_confidence_tracking(
    message: str,
    user_context: Dict,
    conversation_history: List
) -> Dict:
    """
    Wrapper that adds self-assessment to AI responses.
    """
    # Get AI response
    response = await ai_service.chat(message, user_context, conversation_history)
    
    # Ask AI to self-assess confidence
    confidence_check = await ai_service.assess_response_quality(
        question=message,
        answer=response["response"],
        available_context=user_context
    )
    
    # Log for learning
    if confidence_check["confidence"] < 0.7 or confidence_check["missing_data"]:
        await log_learning_opportunity(
            question=message,
            response=response,
            confidence=confidence_check
        )
    
    return {**response, **confidence_check}
```

2. **AI Self-Assessment Prompt**:
```python
CONFIDENCE_ASSESSMENT_PROMPT = """
You just answered a user's question. Assess your response:

Question: {question}
Your Answer: {answer}
Data Available: {context_summary}

Rate your confidence (0.0-1.0) and explain:
1. Did you have all the data needed? If not, what was missing?
2. Were you forced to guess or use general knowledge vs specific user data?
3. Could this answer be more accurate with different data?
4. What database tables/columns would make this answer better?

Respond in JSON:
{
  "confidence": 0.85,
  "had_sufficient_data": true,
  "missing_data": ["user bandwidth usage", "storage quotas"],
  "data_sources_used": ["user_stats", "media_items"],
  "could_improve_with": ["file_size tracking", "bandwidth logs"],
  "reasoning": "I gave a good recommendation based on watch history, but couldn't factor in storage limits"
}
"""
```

3. **Admin Dashboard for AI Learning**:
   - `/admin/ai-insights` page showing:
     - Most asked questions AI struggled with
     - Missing data patterns
     - Suggested database improvements
     - User satisfaction scores
     - Training queue prioritization

---

## Implementation Priority

### Phase 1: Admin AI Chat (This Sprint)
1. ✅ Add admin role check to AI endpoint
2. ⚠️ Add missing columns: `last_login_at`, `file_size_bytes`, `attributed_to_request_id`
3. ⚠️ Create admin-specific AI context builder
4. ⚠️ Add cross-user aggregation queries

### Phase 2: AI Self-Learning (Next Sprint)
1. Create `ai_conversation_feedback` table
2. Create `ai_learning_queue` table
3. Implement confidence tracking wrapper
4. Build admin learning dashboard

### Phase 3: Advanced Analytics (Future)
1. Add `api_logs` table
2. Add `bandwidth_logs` table
3. Implement real-time monitoring
4. Build predictive models

---

## Security Considerations

### Admin vs User Isolation:
- User AI: Only sees their own data (`WHERE user_id = current_user.id`)
- Admin AI: Sees aggregate data (never individual PII unless necessary)
- Admin AI: Cannot access other users' chat history
- Admin AI: Can see patterns, trends, totals - not individual viewing details

### Privacy-Preserving Queries:
```sql
-- Good: "Which genres are most popular?"
SELECT 
  jsonb_array_elements_text(metadata->'genres') as genre,
  COUNT(*) as watch_count
FROM media_items mi
JOIN user_stats us ON us.media_item_id = mi.id
GROUP BY genre;

-- Bad: "What is user X watching?"
-- This requires explicit permission checks
```

---

## Next Steps

Would you like me to:
1. **Add the missing database columns** to migration 006 (last_login_at, file_size_bytes, attributed_to_request_id)?
2. **Create an admin AI endpoint** (`/api/ai/admin/chat`) with cross-user analytics?
3. **Implement the AI self-learning tables** (ai_conversation_feedback, ai_learning_queue)?
4. **All of the above** in sequence?
