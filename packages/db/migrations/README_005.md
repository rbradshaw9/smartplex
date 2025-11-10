# Webhook System Migration

## Migration 005: Webhooks and Sync Schedule

This migration adds the webhook system to SmartPlex.

### Tables Created

1. **webhook_log** - Tracks all incoming webhooks from external services
   - `id` - UUID primary key
   - `source` - Service name (plex, tautulli, sonarr, radarr, overseerr)
   - `event_type` - Type of event (library.new, media.scrobble, etc.)
   - `payload` - Full webhook payload as JSONB
   - `received_at` - Timestamp when webhook was received
   - `processed` - Boolean indicating if webhook was processed
   - `processed_at` - When processing completed
   - `error_message` - Error if processing failed

2. **sync_schedule** - Configurable sync intervals for each service
   - `id` - UUID primary key
   - `service` - Service name
   - `enabled` - Whether scheduled syncs are enabled
   - `interval_hours` - Hours between syncs (1-168, i.e. 1 hour to 1 week)
   - `last_run_at` - Last sync completion time
   - `next_run_at` - Next scheduled sync time
   - `run_count` - Number of syncs completed
   - `last_status` - Status of last sync
   - `last_error` - Error message if last sync failed

### How to Run

1. Go to your Supabase SQL Editor:
   https://supabase.com/dashboard/project/lecunkywsfuqumqzddol/sql/new

2. Copy the contents of `packages/db/migrations/005_add_webhooks_and_sync_schedule.sql`

3. Paste and run in the SQL Editor

### Webhook URLs

Once deployed, configure these webhook URLs in your services:

- **Plex**: `https://your-api.railway.app/api/webhooks/plex`
- **Tautulli**: `https://your-api.railway.app/api/webhooks/tautulli`
- **Sonarr**: `https://your-api.railway.app/api/webhooks/sonarr`
- **Radarr**: `https://your-api.railway.app/api/webhooks/radarr`
- **Overseerr**: `https://your-api.railway.app/api/webhooks/overseerr`

### What This Enables

- **Real-time sync triggers**: Services notify SmartPlex instantly when content changes
- **Event logging**: All webhooks tracked for debugging and statistics
- **Background processing**: Syncs run asynchronously without blocking webhook responses
- **Configurable fallback**: Admin-adjustable scheduled syncs as backup to webhooks
- **Incremental updates**: Webhooks trigger targeted syncs (7 days) instead of full history

### Testing

Check webhook status:
```bash
GET /api/webhooks/status
```

This returns recent webhook counts and processing statistics.
