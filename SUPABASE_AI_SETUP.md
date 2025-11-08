# Supabase Setup for AI Features

## Required Actions in Supabase Dashboard

### 1. Run the AI Enhancement Migration

Execute the SQL migration to add AI-specific tables:

**File:** `packages/db/migrations/002_ai_enhancements.sql`

**Steps:**
1. Go to Supabase Dashboard → SQL Editor
2. Create new query
3. Copy and paste the entire contents of `002_ai_enhancements.sql`
4. Run the query

**This creates:**
- `recommendations` table - Stores AI-generated recommendations
- `user_preferences` table - User AI personalization settings  
- `media_embeddings` table - For future semantic search (requires pgvector)
- `ai_analysis_cache` table - Caches AI analysis to reduce API costs
- Indexes for performance
- Updates to `chat_history` table

### 2. Verify Existing Tables

Make sure these tables from `schema.sql` are already created:
- ✅ `users`
- ✅ `servers`
- ✅ `media_items`
- ✅ `user_stats`
- ✅ `chat_history`

If not, run `schema.sql` first.

### 3. Set Up Row Level Security (RLS)

The `rls.sql` file should already have policies for most tables. 

For the new AI tables, add these policies in SQL Editor:

```sql
-- RLS for recommendations
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own recommendations"
  ON recommendations FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own recommendations"
  ON recommendations FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- RLS for user_preferences
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences"
  ON user_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
  ON user_preferences FOR ALL
  USING (auth.uid() = user_id);

-- RLS for ai_analysis_cache
ALTER TABLE ai_analysis_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analysis"
  ON ai_analysis_cache FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analysis"
  ON ai_analysis_cache FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

### 4. Enable Required Extensions

If using vector embeddings in the future:

```sql
-- Enable pgvector for semantic search (optional - for future feature)
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Verify Railway Environment Variables

Make sure these are set in Railway → Variables:

- `OPENAI_API_KEY` - Your OpenAI API key (already added)
- `SUPABASE_URL` - https://lecunkywsfuqumqzddol.supabase.co
- `SUPABASE_SERVICE_KEY` - Your service role key
- `FRONTEND_URL` - https://smartplex-ecru.vercel.app

## What the AI Stack Does

### Current Implementation:

1. **Real-time Chat** (`/api/ai/chat`)
   - Uses GPT-4 Turbo for intelligent responses
   - Maintains conversation history
   - Provides personalized recommendations
   - Stores all chats in database

2. **Smart Recommendations** (`/api/ai/recommendations`)  
   - Analyzes watch history with AI
   - Generates personalized suggestions
   - Explains reasoning for each recommendation
   - Caches results to reduce API costs

3. **Viewing Analysis** (`/api/ai/analyze`)
   - AI-powered insights about viewing habits
   - Genre preferences and patterns
   - Content discovery suggestions
   - Library optimization tips

### Features:
- ✅ Real OpenAI GPT-4 integration
- ✅ Conversation context and history
- ✅ Personalized based on watch history
- ✅ Stores all interactions in database
- ✅ Caching to minimize API costs
- ✅ Error handling and fallbacks

### Cost Management:
- Using GPT-4 Turbo (cheaper than GPT-4)
- Max 500 tokens per response
- Caches analysis results
- Conversation history limited to last 5 messages

## Testing

After setup, test the AI features:

1. **Chat Endpoint:**
```bash
curl -X POST https://smartplexapi-production.up.railway.app/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "What should I watch tonight?"}'
```

2. **Recommendations:**
```bash
curl https://smartplexapi-production.up.railway.app/api/ai/recommendations?limit=5
```

3. **Analysis:**
```bash
curl -X POST https://smartplexapi-production.up.railway.app/api/ai/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"time_period": "30d", "include_recommendations": true}'
```

## Next Steps

After this is working:

1. **Frontend Integration** - Add chat UI component
2. **Vector Embeddings** - Implement semantic search with embeddings
3. **Advanced Analysis** - More sophisticated viewing pattern analysis
4. **Recommendation Feedback** - Let users rate recommendations
5. **Multi-modal** - Add image analysis for poster/thumbnail insights
