# Database Maintenance Scripts

## fix_invalid_plex_ids.py

### Problem
During Plex sync or data import, some media items may have been stored with invalid `plex_id` values. For example:
- `plex_id: 'Mr. Deeds_2002'` (file name instead of rating key)
- `plex_id: null` or empty string

Valid `plex_id` values must be numeric strings representing Plex rating keys (e.g., `'12345'`).

When the deletion service tries to delete these items, it fails with:
```
invalid literal for int() with base 10: 'Mr. Deeds_2002'
```

### Solution
This script identifies and optionally removes media items with invalid `plex_id` values.

### Usage

**1. Find invalid items (dry run):**
```bash
cd apps/api
python scripts/fix_invalid_plex_ids.py
```

**2. Delete invalid items:**
```bash
python scripts/fix_invalid_plex_ids.py --delete
```

**3. After deletion, re-sync from Plex:**
```bash
# Use the Smartplex web UI to trigger a full Plex sync
# This will re-import the items with correct plex_id values
```

### Prerequisites
Set environment variables:
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_ROLE_KEY="your-service-key"
```

### Output Example
```
🔍 Scanning media_items table for invalid plex_ids...
✅ Scanned 1250 items, found 3 with invalid plex_ids

📋 Invalid plex_id items:

Title                                              Type       Invalid plex_id                ID
------------------------------------------------------------------------------------------------------------------------
Mr. Deeds                                          movie      Mr. Deeds_2002                 abc-123-def
The Matrix                                         movie      Matrix_1999                    xyz-789-uvw
Breaking Bad                                       episode                                   qrs-456-tuv

💡 Actions:
  - To delete these items: python fix_invalid_plex_ids.py --delete
  - To re-sync from Plex: python fix_invalid_plex_ids.py --resync --plex-token YOUR_TOKEN
```

### Prevention
The fix deployed in commit `b87be00` prevents crashes by:
1. Validating `plex_id` is numeric before calling Plex API
2. Raising descriptive error for invalid values
3. Marking items with bad data as "failed" instead of crashing
4. Continuing deletion process for remaining valid items

Items with invalid `plex_id` will now fail gracefully with a clear error message in the logs.
