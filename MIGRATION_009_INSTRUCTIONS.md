# Migration 009 - Ready to Run

## What This Migration Does

### 1. **TV Show Hierarchy Support**
Adds columns to track TV show structure for better aggregation:
- `grandparent_title` - Show name (e.g., "Breaking Bad")
- `parent_title` - Season title (e.g., "Season 1")
- `season_number` - Season number (1, 2, 3...)
- `episode_number` - Episode number within season

### 2. **File Size Optimization**
- Adds `file_size_mb` column (converted from `file_size_bytes`)
- Populates existing rows automatically
- Makes deletion queries much faster

### 3. **System Configuration Table**
Creates new `system_config` table for global settings:
- Store manual storage capacity (GB)
- Extensible for future config needs (sync schedules, etc.)
- Includes default 10TB capacity (you should update this)

### 4. **SQL Functions for Smart Queries**
Three new functions for deletion logic:
- `get_unwatched_shows()` - Find shows with no recent activity
- `get_show_statistics()` - Get complete show stats
- `get_season_statistics()` - Get per-season breakdown

## Running the Migration

### In Supabase Dashboard:

1. Go to: https://supabase.com/dashboard/project/YOUR_PROJECT/sql
2. Copy the entire contents of: `packages/db/migrations/009_tv_show_hierarchy_and_storage.sql`
3. Paste into the SQL Editor
4. Click "Run" (or press Cmd/Ctrl + Enter)

**Expected Results:**
- ✅ 4 new columns added to `media_items`
- ✅ `file_size_mb` populated from `file_size_bytes`
- ✅ `system_config` table created
- ✅ 3 SQL functions created
- ✅ Multiple indexes created for performance
- ✅ Default storage capacity (10TB) inserted

**Time to run:** ~5-10 seconds for most libraries

## After Migration

### Immediate Actions:

1. **Configure Your Actual Storage Capacity:**
   - Go to Deletion Management page
   - Click the ⚙️ settings button in the Storage section
   - Enter your actual capacity (e.g., 10000 GB for 10TB)
   - Click "Save Capacity"

2. **Sync Your Library:**
   - Click "Sync Library" button
   - This will now sync **individual episodes** instead of just shows
   - Progress will show "Show Name - S01E01" format
   - Takes longer but provides episode-level granularity

3. **Sync Tautulli Data (Optional but Recommended):**
   - If you have Tautulli configured:
   - API call: `POST /api/admin/sync/tautulli`
   - Or wait for scheduled sync (we'll add cron later)

### What You'll See:

**Storage Display:**
- Total capacity (if configured)
- Used space with percentage
- Free space remaining
- Color-coded progress bar (green/yellow/red)
- Breakdown by type (movies/episodes)

**Better Deletion Decisions:**
- Can now aggregate by TV show
- See which shows have no recent activity
- Delete entire shows or specific seasons
- Episode-level watch history tracking

## API Changes

### New Endpoints:

**System Config:**
- `GET /api/admin/system/config/storage-capacity` - Get current capacity
- `PUT /api/admin/system/config/storage-capacity` - Update capacity (admin only)
- `GET /api/admin/system/config` - Get all system config (admin only)

**Updated Endpoints:**
- `GET /api/plex/storage-info` - Now includes:
  - `total_capacity_gb` (if configured)
  - `free_gb` (calculated)
  - `used_percentage` (calculated)
  - `capacity_configured` (boolean)

### Database Functions (Can be called via Supabase):

```sql
-- Get unwatched shows for deletion
SELECT * FROM get_unwatched_shows(30, 15);
-- 30 days grace period, 15 days inactivity

-- Get statistics for a specific show
SELECT * FROM get_show_statistics('Breaking Bad');

-- Get per-season stats
SELECT * FROM get_season_statistics('Breaking Bad');
```

## Troubleshooting

### If migration fails:

**Error: "column already exists"**
- Some columns might exist from previous attempts
- Safe to ignore or manually check what's missing

**Error: "function already exists"**
- Functions exist from previous run
- Use `DROP FUNCTION` first or add `OR REPLACE`

**Slow performance:**
- The `file_size_mb` population can take time with large libraries
- Runs in single UPDATE, should be fast (<1 min for 10k items)

### After migration:

**Episodes not showing:**
- Run a full library sync to populate hierarchy fields
- Old syncs only have show-level data
- New syncs will have episode-level data

**Storage capacity not showing:**
- Configure it manually in the UI
- No way to auto-detect without server access

**Deletion rules not finding episodes:**
- After adding hierarchy, you can now query by show
- Update deletion rules to use new SQL functions

## Future Enhancements

With this foundation, you can now:
- Add "Delete entire show" functionality
- Implement "Keep most recent season" logic
- Track episode watch patterns
- Create smarter deletion rules (e.g., "delete shows with <5% episodes watched")
- Schedule automatic Tautulli syncs
- Add Ultra.cc API integration for real disk capacity (if available)

## Questions?

- Check `TAUTULLI_SYNC_ARCHITECTURE.md` for detailed design decisions
- Check `EDGE_CASES_AND_CONSIDERATIONS.md` for known issues
- All endpoints are documented in FastAPI docs: `/docs`
