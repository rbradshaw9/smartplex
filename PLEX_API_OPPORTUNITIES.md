# Plex API Data Opportunities

## What We're Already Capturing ✅

1. **Media Metadata**
   - Title, year, duration, type
   - TMDB/TVDB/IMDB IDs
   - File size (`file_size_bytes`)
   - Added date (`plex_added_at`)

2. **Server Info**
   - Platform, version, machine_id
   - Status, last seen

3. **Basic Analytics**
   - View counts (via Tautulli or Plex API fallback)
   - Last watched date

## Missing Opportunities 🎯

### 1. **Media Quality/Technical Details** (HIGH VALUE)
```python
# Available from media.parts[0]
item.media[0].aspectRatio         # "2.35" 
item.media[0].audioChannels       # 6 (5.1 surround)
item.media[0].audioCodec          # "aac", "dts", "truehd"
item.media[0].bitrate             # 8000 (kbps)
item.media[0].container           # "mkv", "mp4"
item.media[0].duration            # ms
item.media[0].height              # 1080, 2160 (4K)
item.media[0].width               # 1920, 3840
item.media[0].videoCodec          # "h264", "hevc", "av1"
item.media[0].videoFrameRate      # "24p", "60p"
item.media[0].videoResolution     # "1080p", "4k"

# Parts (files)
item.media[0].parts[0].file       # "/movies/Avatar.mkv"
item.media[0].parts[0].size       # bytes (already capturing)
item.media[0].parts[0].accessible # True/False
item.media[0].parts[0].exists     # True/False
```

**Use Cases:**
- **Storage Optimization**: Identify 4K/HEVC candidates for compression
- **Quality Reports**: "You have 50 movies in 1080p that could be upgraded to 4K"
- **Codec Analysis**: "Replace 200GB of H.264 with HEVC to save 40%"
- **Broken Files**: Auto-detect inaccessible/missing files

### 2. **User Watch Progress** (HIGH VALUE)
```python
item.viewOffset                    # ms into playback
item.isPlayed                      # Boolean
item.isPartiallyWatched           # Boolean
item.lastViewedAt                  # datetime (already capturing)
item.viewCount                     # int (already capturing)
```

**Use Cases:**
- **Resume Points**: "Continue watching" with exact position
- **Completion Tracking**: "You're 80% through Breaking Bad"
- **Abandoned Shows**: "10 episodes started but not finished"

### 3. **Content Ratings & Metadata** (MEDIUM VALUE)
```python
item.contentRating                 # "PG-13", "TV-MA"
item.rating                        # 8.5 (critic score)
item.audienceRating               # 9.2 (user score)
item.studio                        # "Warner Bros"
item.originallyAvailableAt        # Release date
item.summary                       # Description (for AI analysis)
item.tagline                       # Short tagline

# Collections & Tags
item.genres                        # [Genre, Genre]
item.directors                     # [Director, Director]
item.writers                       # [Writer, Writer]
item.roles                         # [Actor, Actor] (top-billed)
item.collections                   # ["Marvel Cinematic Universe"]
```

**Use Cases:**
- **AI Recommendations**: "Since you love Christopher Nolan films..."
- **Content Filtering**: "Show me all PG movies for family night"
- **Genre Analytics**: "Your library is 60% action, 20% comedy..."
- **Collection Management**: Auto-organize Marvel movies

### 4. **Subtitle & Audio Tracks** (MEDIUM VALUE)
```python
# From item.media[0].parts[0]
part.audioStreams()                # Multiple audio tracks
part.subtitleStreams()             # Multiple subtitle tracks

# Audio stream details
audio.language                     # "eng", "spa", "jpn"
audio.codec                        # "aac", "dts"
audio.channels                     # 2, 6, 8
audio.bitrate                      # kbps

# Subtitle details  
subtitle.language                  # "eng", "spa"
subtitle.codec                     # "srt", "ass"
subtitle.forced                    # Boolean
```

**Use Cases:**
- **Accessibility**: "23 movies missing English subtitles"
- **Audio Quality**: "Movies with Dolby Atmos"
- **Language Support**: "Content available in Spanish"

### 5. **Server Statistics** (LOW VALUE - mostly cached)
```python
server.activities                  # Current transcodes, scans
server.sessions()                  # Active playback sessions
server.transcodeSessions()         # Active transcodes
server.bandwidth()                 # Bandwidth usage stats
server.resources()                 # CPU/RAM usage (not disk!)
```

**Use Cases:**
- **Activity Monitor**: Show current streams in header
- **Performance**: "Server CPU at 90% during peak hours"
- **Bandwidth**: "Users consumed 500GB this month"

### 6. **Playlists & Collections** (LOW VALUE)
```python
server.playlists()                 # User-created playlists
server.collections()               # User collections
item.collections                   # Collections this item belongs to
```

**Use Cases:**
- **Watch Lists**: Sync Plex playlists to SmartPlex watch lists
- **Collection Sync**: "Leaving Soon" collection auto-updates

### 7. **User Preferences** (LOW VALUE - mostly server-side)
```python
account.subscriptionActive         # Plex Pass status
account.subscriptionFeatures       # ["sync", "cloud", "mobile"]
server.settings                    # Server configuration
```

## Recommended Priorities 🎯

### Phase 1 (Next Sprint):
1. ✅ **Storage is Already Good** - We have `file_size_bytes`, admin sets capacity
2. **Add Media Quality Fields** to `media_items`:
   ```sql
   ALTER TABLE media_items ADD COLUMN video_resolution TEXT;
   ALTER TABLE media_items ADD COLUMN video_codec TEXT;
   ALTER TABLE media_items ADD COLUMN audio_codec TEXT;
   ALTER TABLE media_items ADD COLUMN container TEXT;
   ALTER TABLE media_items ADD COLUMN bitrate_kbps INTEGER;
   ```

3. **Storage Dashboard Enhancements**:
   - Show: "4K: 2TB, 1080p: 3TB, 720p: 500GB"
   - Identify: "H.264 vs HEVC storage savings potential"
   - Alert: "10 files marked as inaccessible/missing"

### Phase 2 (Future):
1. **Watch Progress Tracking** - Resume points per user
2. **Content Quality Reports** - Upgrade suggestions
3. **Activity Monitor** - Live transcode/stream stats in header

### Phase 3 (Nice to Have):
1. **Subtitle/Audio Analysis** - Accessibility reports
2. **Collection Management** - Auto-organize into collections
3. **Bandwidth Analytics** - User consumption tracking

## Storage Capacity - Current Solution ✅

**Status**: PERFECT AS-IS

**What We Have**:
- ✅ Admin sets total capacity in system_config
- ✅ Backend calculates used space from `file_size_bytes`
- ✅ Storage page shows: used/total/percentage/by-type
- ✅ Works for ALL users (local, seedbox, cloud, etc.)

**Why This Works**:
- Every hosting solution is different (local disk, seedbox quota, cloud storage)
- Users know their own limits (10TB drive, 8TB seedbox plan, etc.)
- One-time manual setup is fine (storage limits don't change often)
- No external API dependencies or security concerns

**No Changes Needed** 🎉

## Action Items

1. ✅ **Remove Ultra.cc code** - Not universal, adds complexity
2. ✅ **Keep manual storage config** - Works perfectly
3. **Add media quality tracking** (optional enhancement):
   - Resolution (1080p, 4K)
   - Codecs (H.264, HEVC, AV1)
   - Container (MKV, MP4)
   - Use for storage optimization insights

4. **Document for users**:
   - "Set your total storage capacity in Settings"
   - "SmartPlex calculates usage from your media files"
   - "Storage page shows breakdown by type (movies/shows)"
