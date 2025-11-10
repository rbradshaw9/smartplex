# Webhook Configuration Guide

This guide explains how to configure webhooks in each service to enable real-time sync triggers in SmartPlex.

## Prerequisites

1. **Run the database migration**: Copy and run `packages/db/migrations/005_add_webhooks_and_sync_schedule.sql` in your Supabase SQL Editor
2. **Deploy the API**: Make sure your API is deployed to Railway with the webhook endpoints
3. **Get your webhook URLs**: Replace `YOUR_API_URL` below with your Railway URL (e.g., `https://smartplex-api.up.railway.app`)

## Webhook URLs

```
Plex:      https://YOUR_API_URL/api/webhooks/plex
Tautulli:  https://YOUR_API_URL/api/webhooks/tautulli
Sonarr:    https://YOUR_API_URL/api/webhooks/sonarr
Radarr:    https://YOUR_API_URL/api/webhooks/radarr
Overseerr: https://YOUR_API_URL/api/webhooks/overseerr
```

---

## 1. Plex Webhooks

**What it does**: Notifies SmartPlex when new content is added or media is watched.

### Setup Steps

1. Open Plex Web App: `https://app.plex.tv`
2. Go to **Settings** → **Webhooks**
3. Click **Add Webhook**
4. Enter webhook URL: `https://YOUR_API_URL/api/webhooks/plex`
5. Click **Save Changes**

### Events Handled

- `library.new` - New content added → Triggers library sync
- `media.scrobble` - Content watched/marked as played → Triggers Tautulli sync (7 days)

### Testing

Play a video to completion in Plex, then check:
```bash
GET https://YOUR_API_URL/api/webhooks/status
```

---

## 2. Tautulli Webhooks

**What it does**: Notifies SmartPlex when users stop watching content.

### Setup Steps

1. Open Tautulli web interface
2. Go to **Settings** → **Notification Agents**
3. Click **Add a new notification agent** → **Webhook**
4. Configure:
   - **Webhook URL**: `https://YOUR_API_URL/api/webhooks/tautulli`
   - **Webhook Method**: POST
   - **Triggers**: 
     - ✅ Playback Stop
     - ✅ Watched
5. In the **Data** section, select **JSON**
6. Click **Save**

### Events Handled

- `playback.stop` - User stops watching → Updates watch history
- `watched` - Content marked as watched → Updates watch history

### Payload Fields Used

- `rating_key` - Plex item ID
- `user` - Username who watched
- `title` - Content title
- `media_type` - movie, episode, etc.

---

## 3. Sonarr Webhooks

**What it does**: Notifies SmartPlex when TV episodes are downloaded.

### Setup Steps

1. Open Sonarr web interface
2. Go to **Settings** → **Connect**
3. Click the **+** button → **Webhook**
4. Configure:
   - **Name**: SmartPlex
   - **On Download**: ✅ Enabled
   - **On Upgrade**: ✅ Enabled
   - **URL**: `https://YOUR_API_URL/api/webhooks/sonarr`
   - **Method**: POST
5. Click **Test** to verify connection
6. Click **Save**

### Events Handled

- `Download` - New episode downloaded → Triggers TV Shows library sync
- `Upgrade` - Episode upgraded to better quality → Triggers TV Shows library sync

### What Syncs

When a TV episode is downloaded, SmartPlex:
1. Syncs Plex "TV Shows" library
2. Updates metadata and IDs for the series
3. Matches with TVDb ID from Sonarr

---

## 4. Radarr Webhooks

**What it does**: Notifies SmartPlex when movies are downloaded.

### Setup Steps

1. Open Radarr web interface
2. Go to **Settings** → **Connect**
3. Click the **+** button → **Webhook**
4. Configure:
   - **Name**: SmartPlex
   - **On Download**: ✅ Enabled
   - **On Upgrade**: ✅ Enabled
   - **URL**: `https://YOUR_API_URL/api/webhooks/radarr`
   - **Method**: POST
5. Click **Test** to verify connection
6. Click **Save**

### Events Handled

- `Download` - New movie downloaded → Triggers Movies library sync
- `Upgrade` - Movie upgraded to better quality → Triggers Movies library sync

### What Syncs

When a movie is downloaded, SmartPlex:
1. Syncs Plex "Movies" library
2. Updates metadata and IDs for the movie
3. Matches with TMDb ID from Radarr

---

## 5. Overseerr Webhooks

**What it does**: Notifies SmartPlex when content requests are approved/available.

### Setup Steps

1. Open Overseerr web interface
2. Go to **Settings** → **Notifications** → **Webhook**
3. Configure:
   - **Enable Agent**: ✅ Enabled
   - **Webhook URL**: `https://YOUR_API_URL/api/webhooks/overseerr`
   - **Notification Types**:
     - ✅ Media Requested
     - ✅ Media Approved
     - ✅ Media Available
4. Click **Save Changes**

### Events Handled

- `media.requested` - User requests content → Logs request
- `media.approved` - Request approved → Logs approval
- `media.available` - Content available → Triggers appropriate library sync

### What Syncs

When content becomes available:
- Movies → Triggers Movies library sync
- TV Shows → Triggers TV Shows library sync

---

## Monitoring Webhooks

### Check Webhook Status

```bash
GET https://YOUR_API_URL/api/webhooks/status
```

Returns:
```json
{
  "total_webhooks": 150,
  "by_source": {
    "plex": 50,
    "tautulli": 80,
    "sonarr": 10,
    "radarr": 10
  },
  "recent_webhooks": [
    {
      "source": "plex",
      "event_type": "library.new",
      "received_at": "2024-01-15T10:30:00Z",
      "processed": true
    }
  ]
}
```

### View Logs

Query the `webhook_log` table in Supabase:

```sql
SELECT 
  source,
  event_type,
  received_at,
  processed,
  error_message
FROM webhook_log
ORDER BY received_at DESC
LIMIT 50;
```

### Test Webhook

Use curl to test:

```bash
# Test Plex webhook
curl -X POST https://YOUR_API_URL/api/webhooks/plex \
  -F 'payload={"event":"library.new","Metadata":{"ratingKey":"12345"}}'

# Test Tautulli webhook
curl -X POST https://YOUR_API_URL/api/webhooks/tautulli \
  -H "Content-Type: application/json" \
  -d '{"event":"playback.stop","rating_key":"12345","user":"testuser"}'
```

---

## Troubleshooting

### Webhooks Not Arriving

1. **Check service configuration**: Verify webhook URL is correct
2. **Test endpoint**: Use curl to test webhook endpoint directly
3. **Check logs**: Look at Railway logs for incoming requests
4. **Verify network**: Ensure your service can reach Railway (not blocked by firewall)

### Webhooks Arriving But Not Processing

1. **Check webhook_log**: Query for recent webhooks and error messages
2. **Check API logs**: Look for errors in Railway logs
3. **Verify payload**: Ensure payload matches expected format
4. **Check database**: Verify webhook_log table exists (run migration)

### Background Syncs Not Triggering

1. **Check processing status**: Webhooks should have `processed=true`
2. **Check API logs**: Look for background task execution
3. **Verify dependencies**: Ensure TautulliSyncService is working
4. **Check Plex connection**: Verify Plex server is accessible

---

## Scheduled Sync Configuration

While webhooks handle real-time updates, you can also configure scheduled syncs as a backup:

### View Current Schedule

Query the `sync_schedule` table:

```sql
SELECT * FROM sync_schedule;
```

### Update Sync Interval

```sql
-- Sync Tautulli every 4 hours instead of 6
UPDATE sync_schedule 
SET interval_hours = 4 
WHERE service = 'tautulli';

-- Disable Plex scheduled sync (webhooks only)
UPDATE sync_schedule 
SET enabled = false 
WHERE service = 'plex';
```

### Default Schedule

- **Plex**: 12 hours (webhooks preferred)
- **Tautulli**: 6 hours (webhooks preferred)
- **Sonarr**: 24 hours (disabled, webhooks only)
- **Radarr**: 24 hours (disabled, webhooks only)
- **Overseerr**: 6 hours (disabled, webhooks only)

---

## Architecture

### Event Flow

```
External Service → Webhook → SmartPlex API
                                  ↓
                         Log to webhook_log
                                  ↓
                         Trigger Background Task
                                  ↓
                    Run Incremental Sync (7 days)
                                  ↓
                         Update media_items
```

### Why Event-Driven?

**Before (Polling)**:
- Sync every 6 hours
- Process 90 days of history
- High API usage
- Delayed updates (up to 6 hours)

**After (Webhooks)**:
- Instant notifications
- Process only recent changes (7 days)
- Minimal API usage
- Real-time updates (seconds)

### Benefits

- **Real-time**: Updates within seconds of content changes
- **Efficient**: Only syncs what changed, not entire history
- **Reliable**: Webhooks + scheduled syncs as fallback
- **Transparent**: All events logged for debugging
- **Scalable**: Background processing prevents blocking
