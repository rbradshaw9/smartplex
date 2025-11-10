# Tautulli Sync Architecture & Recommendations

## Current State Analysis

### 1. **Where Does Tautulli Sync Happen?**

**No, `plex_sync.py` does NOT sync Tautulli data.** You have two separate sync systems:

#### A. Plex Sync (`apps/api/app/api/routes/plex_sync.py`)
- **Purpose**: Syncs media metadata from Plex API
- **What it does**:
  - Connects to Plex servers
  - Scans library sections (movies, TV shows)
  - Creates/updates `media_items` table with:
    - `plex_id`, `title`, `year`, `type`, `tmdb_id`, `tvdb_id`
    - `file_path`, `file_size_bytes`, `added_at`
    - Basic metadata from Plex
- **Does NOT sync**: Watch history, play counts, or viewing statistics

#### B. Tautulli Sync (`apps/api/app/services/tautulli_sync.py`)
- **Purpose**: Syncs aggregated watch statistics from Tautulli
- **What it does**:
  - Fetches watch history from Tautulli API (`get_history`)
  - Aggregates by `rating_key` (Plex item ID)
  - Updates `media_items` table with:
    - `total_play_count`: Total plays across ALL users
    - `last_watched_at`: Most recent watch by ANY user
    - `total_watch_time_seconds`: Total watch time across ALL users
    - `tautulli_synced_at`: Timestamp of sync
- **Critical**: Aggregates across ALL Plex users, not just SmartPlex users

### 2. **Database Schema for Aggregated Stats**

From `004_add_tautulli_stats.sql`:

```sql
ALTER TABLE media_items 
ADD COLUMN total_play_count INTEGER DEFAULT 0;

ALTER TABLE media_items 
ADD COLUMN last_watched_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE media_items 
ADD COLUMN total_watch_time_seconds BIGINT DEFAULT 0;

ALTER TABLE media_items 
ADD COLUMN tautulli_synced_at TIMESTAMP WITH TIME ZONE;
```

**These columns store SERVER-WIDE metrics**, perfect for admin deletion decisions.

---

## TV Show Handling: Best Practices

### Current Problem
TV shows have a hierarchy:
- **Show** (e.g., "Breaking Bad")
  - **Season 1**
    - Episode 1, Episode 2, etc.
  - **Season 2**
    - Episode 1, Episode 2, etc.

Tautulli tracks **individual episode plays**, but deletions often happen at **show** or **season** level.

### Recommended Approach: **Hierarchical Aggregation**

#### Option 1: Store Episode-Level (CURRENT - Already in DB)
```
media_items table:
- Show: Breaking Bad (type='show', no stats)
  - Episode: S01E01 (type='episode', total_play_count=5, last_watched_at='2025-11-01')
  - Episode: S01E02 (type='episode', total_play_count=3, last_watched_at='2025-10-15')
  - Episode: S02E01 (type='episode', total_play_count=0, last_watched_at=NULL)
```

**For deletion decisions, aggregate on-the-fly:**
- "Has Breaking Bad been watched in last 30 days?" → Check `MAX(last_watched_at)` for all episodes
- "How many times was Season 1 watched?" → `SUM(total_play_count)` for S01 episodes
- "Is the show completely unwatched?" → Check if `SUM(total_play_count) = 0` for all episodes

**SQL Example:**
```sql
-- Find shows where NO episode was watched in 30+ days
SELECT 
  parent_title AS show_name,
  MAX(last_watched_at) AS most_recent_watch,
  SUM(total_play_count) AS total_show_plays,
  COUNT(*) AS total_episodes,
  SUM(file_size_mb) AS total_show_size_mb
FROM media_items
WHERE type = 'episode'
  AND (last_watched_at IS NULL OR last_watched_at < NOW() - INTERVAL '30 days')
GROUP BY parent_title, tvdb_id
HAVING SUM(total_play_count) = 0 OR MAX(last_watched_at) < NOW() - INTERVAL '30 days'
ORDER BY SUM(file_size_mb) DESC;
```

#### Why Episode-Level is Best:
1. ✅ **Accurate**: Tautulli tracks episodes, not shows
2. ✅ **Flexible**: Can decide to delete entire show, specific seasons, or unwatched episodes
3. ✅ **Storage-aware**: Can identify "watched S01-S03, unwatched S04-S06" patterns
4. ✅ **No data loss**: Preserve granular watch history
5. ✅ **Scalable**: Aggregation queries are fast with proper indexes

---

## Storage Data from Ultra.cc

### Question: Can We Get Total Disk Capacity?

**Tautulli does NOT provide filesystem storage data.** Tautulli only knows about:
- Play history (who watched what, when)
- Media file sizes (from Plex metadata)
- Streaming stats

**Ultra.cc Storage Options:**

1. **SSH/SFTP Access** (if available):
   ```bash
   df -h /path/to/media
   ```
   - Requires Ultra.cc credentials
   - Could run periodically via scheduled task
   - Store in new `storage_stats` table

2. **Ultra.cc API** (check if they have one):
   - Some seedbox providers expose disk usage API
   - Would need API documentation

3. **Plex API (Current)**: 
   - Only shows media file sizes
   - Cannot see total disk capacity
   - This is what you have now

4. **Database Calculation (Best for now)**:
   ```sql
   SELECT 
     SUM(file_size_mb) AS total_media_gb / 1024,
     COUNT(*) AS total_files
   FROM media_items;
   ```
   - Fast, accurate for media files
   - Doesn't show free space, but shows what Plex manages

**Recommendation**: Add a manual "Total Capacity" setting in admin config:
```sql
CREATE TABLE system_config (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO system_config (key, value) VALUES 
('storage_capacity_gb', '{"total_gb": 10000, "updated_at": "2025-11-10", "source": "manual"}');
```

Then calculate:
- **Used**: `SUM(file_size_mb) / 1024` from database
- **Free**: `total_gb - used_gb`
- **Percentage**: `(used_gb / total_gb) * 100`

---

## Deletion Page Requirements

### You're Right: Admin Deletion MUST Use Aggregated Data

From your message:
> "the deletion page is an admin page, it MUST use aggregated data across all users. We need to know exactly when it was added, when it was last watched/accessed by ANY user."

**Current State**: ✅ **Already designed for this!**

The `media_items` table has:
- `added_at`: When Plex added the item (from Plex sync)
- `total_play_count`: Plays by ALL users (from Tautulli)
- `last_watched_at`: Most recent watch by ANY user (from Tautulli)
- `total_watch_time_seconds`: Total watch time across ALL users (from Tautulli)

**Deletion rule example:**
```sql
SELECT 
  id, title, type, 
  added_at,
  last_watched_at,
  total_play_count,
  file_size_mb,
  EXTRACT(DAY FROM NOW() - added_at) AS days_since_added,
  EXTRACT(DAY FROM NOW() - COALESCE(last_watched_at, added_at)) AS days_since_watched
FROM media_items
WHERE 
  -- Grace period: added 30+ days ago
  added_at < NOW() - INTERVAL '30 days'
  -- Inactivity: not watched in 15+ days (or never watched)
  AND (last_watched_at IS NULL OR last_watched_at < NOW() - INTERVAL '15 days')
  -- Optional: low play count
  AND total_play_count < 2
ORDER BY file_size_mb DESC;
```

---

## Sync Strategy: Store vs Query On-Demand

### Question: Should we sync Tautulli and store everything, or query each time?

**Recommendation: STORE aggregated stats (current approach is correct)**

#### Why Store is Better:

1. **Performance**:
   - Tautulli API calls are SLOW (100-200ms each)
   - Fetching 10,000+ episodes would take minutes
   - Database query: <1 second

2. **Reliability**:
   - Tautulli might be offline
   - Deletion decisions shouldn't fail due to API unavailability
   - Database is always available

3. **Historical tracking**:
   - Can track when stats were last updated (`tautulli_synced_at`)
   - Can show "last synced X minutes ago" in UI
   - Can trigger sync if data is stale

4. **Admin efficiency**:
   - Admins scan/filter/sort hundreds of items
   - Every sort/filter would hit Tautulli API
   - With DB: instant sorting, filtering, pagination

#### Sync Schedule:

```python
# Option 1: Periodic background sync (RECOMMENDED)
# Run every 6-12 hours via cron/scheduler
await tautulli_sync_service.sync_watch_history(days_back=90)

# Option 2: Webhook-triggered sync
# When Plex webhook fires for "media.play", trigger mini-sync for that item

# Option 3: On-demand sync with cache
# "Sync Now" button in admin UI, but show cached data while syncing
```

**Best Practice**: 
- Background sync every 12 hours (overnight + midday)
- "Last synced" indicator in UI
- "Sync Now" button for admins
- Cache TTL: 6 hours

---

## TV Show Aggregation: Implementation

### Add Helper Columns to `media_items`

```sql
-- Add parent/grandparent references for TV shows
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS parent_title TEXT,        -- Season title (for episodes)
ADD COLUMN IF NOT EXISTS grandparent_title TEXT,   -- Show title (for episodes)
ADD COLUMN IF NOT EXISTS season_number INTEGER,    -- Season # (for episodes)
ADD COLUMN IF NOT EXISTS episode_number INTEGER;   -- Episode # (for episodes)

-- Index for fast aggregation
CREATE INDEX idx_media_items_show_hierarchy 
ON media_items(grandparent_title, season_number, episode_number) 
WHERE type = 'episode';
```

### Populate During Sync

In `plex_sync.py`, when syncing episodes:
```python
if item.type == 'episode':
    media_data = {
        'title': item.title,
        'type': 'episode',
        'parent_title': item.seasonTitle,           # "Season 1"
        'grandparent_title': item.grandparentTitle, # "Breaking Bad"
        'season_number': item.seasonNumber,         # 1
        'episode_number': item.episodeNumber,       # 5
        # ... other fields
    }
```

### Query for Deletion Candidates

```python
# Find unwatched shows
unwatched_shows = supabase.rpc('get_unwatched_shows', {
    'days_since_added': 30,
    'days_since_watched': 15
}).execute()

# SQL function:
"""
CREATE OR REPLACE FUNCTION get_unwatched_shows(
  days_since_added INTEGER,
  days_since_watched INTEGER
)
RETURNS TABLE (
  show_title TEXT,
  tvdb_id INTEGER,
  total_episodes INTEGER,
  total_size_gb NUMERIC,
  last_watched_at TIMESTAMP WITH TIME ZONE,
  added_at TIMESTAMP WITH TIME ZONE,
  total_plays INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    grandparent_title AS show_title,
    MAX(tvdb_id) AS tvdb_id,
    COUNT(*) AS total_episodes,
    ROUND(SUM(file_size_mb) / 1024.0, 2) AS total_size_gb,
    MAX(last_watched_at) AS last_watched_at,
    MIN(added_at) AS added_at,
    SUM(total_play_count) AS total_plays
  FROM media_items
  WHERE type = 'episode'
    AND grandparent_title IS NOT NULL
  GROUP BY grandparent_title, tvdb_id
  HAVING 
    MIN(added_at) < NOW() - (days_since_added || ' days')::INTERVAL
    AND (MAX(last_watched_at) IS NULL 
         OR MAX(last_watched_at) < NOW() - (days_since_watched || ' days')::INTERVAL)
  ORDER BY SUM(file_size_mb) DESC;
END;
$$ LANGUAGE plpgsql;
"""
```

---

## Recommended Migration: Add TV Show Hierarchy

### Migration 009: Enhanced TV Show Support

```sql
-- Migration: 009_tv_show_hierarchy.sql
-- Add TV show hierarchy fields for better aggregation

-- Add hierarchy columns
ALTER TABLE media_items 
ADD COLUMN IF NOT EXISTS parent_title TEXT,
ADD COLUMN IF NOT EXISTS grandparent_title TEXT,
ADD COLUMN IF NOT EXISTS season_number INTEGER,
ADD COLUMN IF NOT EXISTS episode_number INTEGER;

-- Add constraints
ALTER TABLE media_items 
ADD CONSTRAINT media_items_season_check 
CHECK (season_number IS NULL OR season_number >= 0);

ALTER TABLE media_items 
ADD CONSTRAINT media_items_episode_check 
CHECK (episode_number IS NULL OR episode_number >= 0);

-- Add indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_media_items_grandparent_title 
ON media_items(grandparent_title) 
WHERE type = 'episode';

CREATE INDEX IF NOT EXISTS idx_media_items_show_hierarchy 
ON media_items(grandparent_title, season_number, episode_number) 
WHERE type = 'episode';

CREATE INDEX IF NOT EXISTS idx_media_items_season 
ON media_items(grandparent_title, season_number) 
WHERE type = 'episode';

-- Add comments
COMMENT ON COLUMN media_items.parent_title IS 
'Season title for episodes (e.g., "Season 1")';

COMMENT ON COLUMN media_items.grandparent_title IS 
'Show title for episodes (e.g., "Breaking Bad")';

COMMENT ON COLUMN media_items.season_number IS 
'Season number for episodes (1-based)';

COMMENT ON COLUMN media_items.episode_number IS 
'Episode number within season (1-based)';
```

---

## Action Items

### Immediate (HIGH Priority):

1. **✅ Already Done**: Tautulli sync service exists
2. **✅ Already Done**: Aggregated stats columns in `media_items`
3. **🔴 TODO**: Run Migration 009 (add TV show hierarchy)
4. **🔴 TODO**: Update `plex_sync.py` to populate hierarchy fields
5. **🔴 TODO**: Add scheduled Tautulli sync (every 12 hours)
6. **🔴 TODO**: Add "Last Synced" indicator to deletion page UI

### Medium Priority:

7. **🟡 TODO**: Create `get_unwatched_shows()` SQL function
8. **🟡 TODO**: Update deletion scanning to aggregate by show
9. **🟡 TODO**: Add "Group by Show" toggle in deletion UI
10. **🟡 TODO**: Add manual storage capacity config

### Low Priority:

11. **🟢 TODO**: Investigate Ultra.cc API for disk usage
12. **🟢 TODO**: Add Tautulli webhook support for real-time updates
13. **🟢 TODO**: Add per-season deletion option

---

## Summary

### Your Questions Answered:

1. **Is plex_sync.py where Tautulli sync happens?**
   - No, `plex_sync.py` only syncs Plex metadata
   - `tautulli_sync.py` syncs watch statistics
   - They are separate processes

2. **Should we store metadata with the file?**
   - ✅ **YES** - Store aggregated stats in `media_items`
   - Much faster than querying Tautulli API every time
   - Already implemented correctly

3. **How to handle TV shows?**
   - ✅ **Store episodes individually** (current approach)
   - Add hierarchy fields (show title, season #, episode #)
   - Aggregate on-demand with SQL queries
   - Best balance of granularity and flexibility

4. **Store or query Tautulli each time?**
   - ✅ **STORE** - Current approach is correct
   - Query Tautulli periodically (12 hours)
   - Use database for all deletion decisions
   - Much faster, more reliable

5. **Ultra.cc storage data?**
   - ❌ Not available in Tautulli
   - Options: SSH/SFTP, Ultra.cc API, or manual config
   - For now: use database for media sizes + manual total capacity

### Next Steps:

Would you like me to:
1. Create Migration 009 for TV show hierarchy?
2. Update `plex_sync.py` to populate hierarchy fields?
3. Add scheduled Tautulli sync endpoint?
4. Create the `get_unwatched_shows()` SQL function?
5. Add storage capacity configuration?

Let me know which you'd like to tackle first!
