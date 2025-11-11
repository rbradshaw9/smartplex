# Deletions Feature - Complete Testing Checklist

## Pre-Test Setup ✅

### 1. Verify Database Population
- [ ] Navigate to `/admin/deletion` page
- [ ] Check storage shows **1980 items** (not 1000)
- [ ] Verify storage shows ~3353 GB total
- [ ] If count is wrong, refresh page and check Railway logs

### 2. Setup Tautulli Integration
- [ ] Go to `/admin/integrations`
- [ ] Add Tautulli integration if not already done
- [ ] Test connection (should return green ✅)
- [ ] Click "Sync Last 90 Days" button
- [ ] Wait for sync to complete (~30-60 seconds)
- [ ] Verify success message shows items fetched/updated

### 3. Verify Watch Stats Populated
- [ ] Open Supabase → SQL Editor
- [ ] Run: `SELECT COUNT(*) FROM media_items WHERE last_watched_at IS NOT NULL;`
- [ ] Should return > 0 (shows Tautulli data synced)
- [ ] Run: `SELECT title, last_watched_at, total_play_count FROM media_items WHERE last_watched_at IS NOT NULL LIMIT 10;`
- [ ] Verify realistic watch dates and counts

---

## Test 1: Create Deletion Rule ✅

### Steps:
1. Go to `/admin/deletion`
2. Click "+ Create Rule" button
3. Fill in form:
   - **Name**: "Test Rule - 90 Days Inactive"
   - **Description**: "Test deletion of unwatched content"
   - **Enabled**: ❌ (keep disabled for testing)
   - **Dry Run Mode**: ✅ (always on for safety)
   - **Grace Period**: 30 days
   - **Inactivity Threshold**: 90 days
   - **Excluded Genres**: (leave empty for now)
   - **Min Rating**: (leave empty)
4. Click "Save Rule"

### Expected Results:
- ✅ Rule appears in rules list
- ✅ Shows "Disabled" status badge
- ✅ Shows creation date

---

## Test 2: Scan for Candidates ✅

### Steps:
1. Find your test rule in the list
2. Click "Scan" button
3. Wait for scan to complete (~5-10 seconds)

### Expected Results:
- ✅ Shows "Found X candidates" message
- ✅ Displays table with candidates showing:
  - Title
  - Type (movie/show)
  - Days since added
  - Days since viewed
  - View count (from Tautulli)
  - File size
  - Rating (if available)
- ✅ Candidates are sorted by days_since_viewed (DESC)
- ✅ All candidates meet criteria:
  - Added > 30 days ago (grace period)
  - Not viewed in > 90 days (inactivity)

### Verify "Leaving Soon" Collection:
- [ ] Open Plex web interface
- [ ] Navigate to Movies library → Collections
- [ ] Should see "Leaving Soon ⏰" collection
- [ ] Collection should contain movies from scan
- [ ] Navigate to TV Shows library → Collections
- [ ] Should see "Leaving Soon ⏰" collection
- [ ] Collection should contain shows from scan
- [ ] Summary should say "These items are candidates for deletion..."

---

## Test 3: Filter and Sort Candidates ✅

### Steps:
1. With candidates displayed, test filters:
   - Click "Movies" filter → should show only movies
   - Click "TV Shows" filter → should show only shows
   - Click "All" → should show both
2. Test sorting:
   - Click column headers (Title, Days Since Added, etc.)
   - Should re-sort table

### Expected Results:
- ✅ Filters work in real-time
- ✅ Sort changes visual order
- ✅ Counts update correctly

---

## Test 4: Dry Run Deletion ✅

### Steps:
1. With candidates displayed, click "Execute Deletion (Dry Run)" button
2. Wait for dry run to complete

### Expected Results:
- ✅ Alert shows:
  - "Dry Run Complete!"
  - Would delete: X items
  - Failed: 0 items
  - Space to free: XXX MB
- ✅ No actual files deleted
- ✅ Plex library unchanged
- ✅ Candidates still in scan results

### Check Logs:
- [ ] Open Railway → Logs
- [ ] Search for "DRY RUN"
- [ ] Should see log entries for each candidate
- [ ] Should show "Would delete from Plex"
- [ ] Should show cascade results (Sonarr/Radarr/Overseerr)

---

## Test 5: Select Specific Candidates ✅

### Steps:
1. In candidates table, use checkboxes to select 1-2 unwanted items
2. Click "Delete Selected" button
3. Confirm you selected the right items
4. Execute dry run first

### Expected Results:
- ✅ Only selected items processed
- ✅ Dry run shows correct count
- ✅ Other candidates remain unaffected

---

## Test 6: Real Deletion (DESTRUCTIVE) 🚨

**⚠️ WARNING: This actually deletes files! Only proceed if you're ready.**

### Pre-Deletion Verification:
- [ ] Identify ONE test item you're okay deleting
- [ ] Note its title, file path, and size
- [ ] Check it exists in Plex library
- [ ] Check if it's in Sonarr/Radarr (if applicable)
- [ ] Take screenshot for comparison

### Steps:
1. Select ONLY the test item checkbox
2. Click "Execute Deletion" (without Dry Run)
3. Read confirmation dialog **carefully**
4. Type "DELETE" in all caps
5. Confirm and wait for completion (~10-30 seconds depending on integrations)

### Expected Results:
- ✅ Success alert shows:
  - Deleted: 1 item
  - Failed: 0 items
  - Space freed: XXX MB
- ✅ Item removed from scan results
- ✅ Storage count decreases by 1

### Verify Cascade Deletion:
1. **Plex Library** 🎬
   - [ ] Open Plex web interface
   - [ ] Search for deleted item
   - [ ] Should NOT be found
   - [ ] Verify file physically deleted from server storage

2. **Database** 💾
   - [ ] Open Supabase → Table Editor → media_items
   - [ ] Search for deleted item by title
   - [ ] Should NOT be found (row deleted)

3. **Sonarr (if TV show)** 📺
   - [ ] Open Sonarr web interface
   - [ ] Search for deleted series
   - [ ] Should NOT be found (removed from Sonarr)
   - [ ] Prevents auto-redownload ✅

4. **Radarr (if movie)** 🎬
   - [ ] Open Radarr web interface
   - [ ] Search for deleted movie
   - [ ] Should NOT be found (removed from Radarr)
   - [ ] Prevents auto-redownload ✅

5. **Overseerr (if requested)** 🎭
   - [ ] Open Overseerr web interface
   - [ ] Search for deleted item
   - [ ] Request should be cleared or marked "not available"
   - [ ] User can request again if desired ✅

6. **Audit Logs** 📋
   - [ ] Go to Supabase → Table Editor → deletion_events
   - [ ] Find record for deleted item
   - [ ] Verify fields populated:
     - `deleted_from_plex`: true
     - `deleted_from_sonarr/radarr`: true (if applicable)
     - `deleted_from_overseerr`: true (if applicable)
     - `status`: "completed"
     - `completed_at`: timestamp

---

## Test 7: Multi-Tenancy (if applicable) 🏢

### If you have multiple servers or users:
1. Create test user account
2. Add to `server_members` table with role="viewer"
3. Log in as test user
4. Verify they CANNOT access `/admin/deletion` (403)
5. Verify requests use correct server's integrations

---

## Test 8: Webhooks Verification 🪝

### Plex Webhook:
1. Watch a short video to 90%+ completion
2. Check Railway logs for "Plex webhook received"
3. Verify Tautulli sync triggered
4. Check `media_items` table for updated `last_watched_at`

### Sonarr/Radarr Webhook (if configured):
1. Add a new movie/show via Sonarr/Radarr
2. Check Railway logs for webhook received
3. Verify library sync triggered
4. Check `media_items` table for new entry

---

## Test 9: Storage Stats Accuracy 📊

### Steps:
1. Note total items and GB before deletion
2. Delete 1 item with known file size
3. Refresh `/admin/deletion` page
4. Verify storage updated:
   - Total items decreased by 1
   - Total GB decreased by file size

### Expected Results:
- ✅ Storage stats update in real-time
- ✅ Counts match reality
- ✅ No "items_without_size" warning (or very few)

---

## Test 10: "Leaving Soon" Collection Management 🏷️

### After Deletion:
- [ ] Open Plex → Collections
- [ ] Verify deleted items removed from "Leaving Soon"
- [ ] Remaining candidates still present

### Clear Collection:
- [ ] In `/admin/deletion`, click "Clear Leaving Soon Collection" (if button exists)
- [ ] Verify collection emptied in Plex
- [ ] Users no longer see warnings

---

## Performance Testing ⚡

### Large-Scale Scan:
1. Create rule with loose criteria (e.g., 7 days inactivity)
2. Scan for candidates (should find many)
3. Measure:
   - [ ] Scan completes in < 30 seconds for 1980 items
   - [ ] Page remains responsive
   - [ ] No timeouts or 502 errors

### Bulk Deletion (if brave):
1. Select 10+ candidates
2. Execute deletion
3. Measure:
   - [ ] All deletions complete successfully
   - [ ] No partial failures
   - [ ] Logs show cascade for each item
   - [ ] Total time < 1 minute per item

---

## Edge Cases & Error Handling 🐛

### Test Error Scenarios:
1. **Item already deleted in Plex**:
   - [ ] Manually delete item from Plex
   - [ ] Try to delete via SmartPlex
   - [ ] Should handle gracefully with error message

2. **Integration offline**:
   - [ ] Stop Sonarr/Radarr/Overseerr
   - [ ] Execute deletion
   - [ ] Should mark as "partial success" (Plex deleted, arr failed)

3. **No candidates found**:
   - [ ] Create rule with impossible criteria (e.g., 10000 days inactive)
   - [ ] Scan should return 0 candidates
   - [ ] Should show friendly message

4. **Concurrent scans**:
   - [ ] Open two browser tabs
   - [ ] Trigger scans in both simultaneously
   - [ ] Both should complete without corruption

---

## Final Checklist ✅

Before considering deletions "production ready":

- [ ] Storage count accurate (1980 items shown)
- [ ] Tautulli watch stats populating correctly
- [ ] Can create/edit/delete rules without errors
- [ ] Scan returns correct candidates based on criteria
- [ ] Dry run works without side effects
- [ ] Real deletion successfully removes files
- [ ] Cascade deletion works for all integrations (Plex/Sonarr/Radarr/Overseerr)
- [ ] Audit logs capture all events
- [ ] "Leaving Soon" collection updates automatically
- [ ] Webhooks triggering and syncing data
- [ ] Multi-tenancy prevents unauthorized access
- [ ] Performance acceptable for 1980+ items
- [ ] Error handling graceful for edge cases
- [ ] No data corruption or orphaned records

---

## Known Limitations 🚧

- Sync performance: ~5-10 items/second (optimizations in progress)
- "Leaving Soon" collection requires Plex token with admin access
- Webhook setup is manual (no auto-configuration yet)
- Ultra.cc API integration not yet implemented (manual capacity config)
- No batch operations UI (select all, delete all)
- No scheduled/automated deletions (manual trigger only)

---

## Next Steps 🚀

After testing completes:

1. **Implement Ultra.cc API** - Auto-fetch storage capacity
2. **Optimize sync performance** - Batch operations, parallel API calls
3. **Add scheduled rules** - Cron jobs for automatic deletion
4. **Email notifications** - Alert users before deletion
5. **Restore functionality** - Undo accidental deletions (if files backed up)
6. **Usage analytics** - Track deletion patterns and savings
7. **Advanced filters** - By IMDb rating, genre, year, etc.
8. **Bulk actions UI** - Select all, delete all with one click

---

## Need Help? 🆘

- **Storage count still wrong?** Check Railway logs for "Storage info" log line
- **Tautulli not syncing?** Verify integration test passes and API key is correct
- **Candidates list empty?** Loosen criteria (lower inactivity days)
- **Deletion failed?** Check cascade_details in response for specific integration errors
- **Collection not updating?** Verify Plex token has admin access to server
- **Webhooks not working?** Check WEBHOOKS_SETUP.md for correct URLs and triggers

---

**Last Updated**: 2025-01-11
**Version**: 1.0.0 - Initial Release
