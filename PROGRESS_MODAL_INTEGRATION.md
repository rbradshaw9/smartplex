# Deletion Progress Modal Integration Guide

## What's Already Done ✅

1. **DeletionProgressModal component** created at `apps/web/src/components/DeletionProgressModal.tsx`
2. **Backend progress tracking** added to `apps/api/app/api/routes/admin_deletion.py`:
   - In-memory progress store per user
   - `/api/admin/deletion/progress` endpoint
   - Progress updates during deletion loop
3. **Progress polling hook** created at `apps/web/src/hooks/useDeletionProgress.ts`
4. **Frontend state prepared** in `apps/web/src/app/admin/deletion/page.tsx`

## Integration Steps (Easy!)

### Step 1: Import the hook
In `/apps/web/src/app/admin/deletion/page.tsx`, add this import at the top:

```typescript
import { useDeletionProgress } from '@/hooks/useDeletionProgress'
```

### Step 2: Use the hook
After the existing state declarations (around line 50), add:

```typescript
// Progress hook
const { progress, startPolling, stopPolling, reset } = useDeletionProgress(
  process.env.NEXT_PUBLIC_API_URL || '',
  '' // Will be updated when we have session
)
```

### Step 3: Update the executeDeletion function
Find the `const executeDeletion = async (dryRun: boolean) => {` function (around line 800) and replace the entire function with this:

```typescript
const executeDeletion = async (dryRun: boolean) => {
  if (!dryRun) {
    const confirmMessage = `⚠️ WARNING: You are about to PERMANENTLY DELETE ${selectedCandidates.size} items!

Files will be DELETED from your server storage.
This CANNOT be undone.

Type "DELETE" below to confirm:`
    
    const userInput = prompt(confirmMessage)
    if (userInput !== 'DELETE') {
      alert('Deletion cancelled. (You must type DELETE in all caps to confirm)')
      return
    }
  }

  setExecuting(true)
  setError('')

  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session || !scanResults) return

    // Get Plex token from localStorage
    const plexToken = localStorage.getItem('plex_token')
    if (!plexToken) {
      setError('Plex token not found. Please reconnect to your Plex server.')
      setExecuting(false)
      return
    }

    // Show progress modal and start polling
    setShowProgressModal(true)
    setDeletionProgress({
      current: 0,
      total: selectedCandidates.size,
      deleted: 0,
      failed: 0,
      currentItem: '',
      status: 'processing',
      message: `Starting deletion of ${selectedCandidates.size} items...`
    })
    
    // Start polling for progress updates
    startPolling()

    // Start the deletion (don't await - let it run in background)
    fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/execute`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          rule_id: scanResults.rule_id, 
          dry_run: dryRun,
          candidate_ids: Array.from(selectedCandidates),
          plex_token: plexToken
        })
      }
    ).then(async (response) => {
      if (response.ok) {
        // Clear selection and reload
        setSelectedCandidates(new Set())
        setScanResults(null)
        loadRules()
        loadStorageInfo()
      } else {
        const error = await response.json()
        setError(`Failed: ${error.detail || 'Unknown error'}`)
        setDeletionProgress(prev => ({
          ...prev,
          status: 'error',
          message: error.detail || 'Deletion failed'
        }))
        stopPolling()
      }
      setExecuting(false)
    }).catch((err) => {
      setError(`Network Error: ${err instanceof Error ? err.message : 'Failed'}`)
      setDeletionProgress(prev => ({
        ...prev,
        status: 'error',
        message: 'Network error occurred'
      }))
      stopPolling()
      setExecuting(false)
    })

  } catch (err) {
    const errorMsg = `Error: ${err instanceof Error ? err.message : 'Failed to execute deletion'}`
    setError(errorMsg)
    setExecuting(false)
    stopPolling()
  }
}
```

### Step 4: Add the modal to the JSX
At the END of the return statement (right before the final `</div></div>`), add:

```tsx
      {/* Deletion Progress Modal */}
      <DeletionProgressModal
        isOpen={showProgressModal}
        onClose={() => {
          setShowProgressModal(false)
          reset()
        }}
        isDryRun={false}
        progress={deletionProgress}
      />
    </div>
  </div>
```

### Step 5: Update progress from polling
Add this useEffect to sync the polled progress with the local state:

```typescript
// Sync polled progress with local state
useEffect(() => {
  if (progress.status !== 'idle') {
    setDeletionProgress({
      current: progress.current,
      total: progress.total,
      deleted: progress.deleted,
      failed: progress.failed,
      currentItem: progress.currentItem || '',
      status: progress.status,
      message: progress.message || ''
    })
  }
}, [progress])
```

## Testing

1. **Deploy**: Push to GitHub (Railway auto-deploys backend, Vercel auto-deploys frontend)
2. **Test**: Select multiple movies (10-20) and click Delete
3. **Observe**: Modal should show with live progress updates every second
4. **Verify**: Check Railway logs to see progress logging every 5 items

## What You'll See

When you delete 41 movies:
- Modal opens immediately
- Progress bar animates 0% → 100%
- "Currently processing: Movie Title" updates in real-time
- Stats update: "Deleted: 5", "Failed: 0", etc.
- Takes ~3-4 minutes for 41 items (5s each + 0.1s delay)
- Modal shows "✅ Completed: 41 deleted, 0 failed" when done
- Click "Close" to dismiss

## Key Features

- **Non-blocking**: Page remains responsive during deletion
- **Real-time**: Progress updates every 1 second
- **Resilient**: Continues polling even if individual API calls fail
- **Clear feedback**: Shows current item being processed
- **Graceful completion**: Auto-stops polling when done
