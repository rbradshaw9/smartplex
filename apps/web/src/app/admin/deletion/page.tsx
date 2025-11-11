'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { Database } from '@smartplex/db'

interface DeletionRule {
  id: string
  name: string
  description: string | null
  enabled: boolean
  dry_run_mode: boolean
  grace_period_days: number
  inactivity_threshold_days: number
  excluded_libraries: string[]
  excluded_genres: string[]
  min_rating: number | null
  last_run_at: string | null
  created_at: string
  updated_at: string
}

interface DeletionCandidate {
  id: string
  plex_id: string
  title: string
  type: string
  parent_title?: string | null  // TV show name for episodes
  season_number?: number | null  // Season number for episodes
  episode_number?: number | null  // Episode number
  date_added: string
  last_viewed_at: string
  view_count: number
  days_since_added: number
  days_since_viewed: number
  rating: number | null
  file_size_mb: number | null
}

interface ScanResults {
  rule_id: string
  total_candidates: number
  candidates: DeletionCandidate[]
}

export default function DeletionManagementPage() {
  const router = useRouter()
  const [supabase] = useState(() => createClientComponentClient<Database>())
  const [rules, setRules] = useState<DeletionRule[]>([])
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncProgress, setSyncProgress] = useState({ current: 0, total: 0, eta: '', title: '', section: '', itemsPerSecond: 0 })
  const [syncEventSource, setSyncEventSource] = useState<EventSource | null>(null)
  const [storageInfo, setStorageInfo] = useState<{ 
    total_items: number
    total_used_gb: number
    total_used_tb: number
    total_capacity_gb?: number | null
    free_gb?: number | null
    used_percentage?: number | null
    capacity_configured: boolean
    by_type?: Record<string, { count: number; size_gb: number }>
  } | null>(null)
  const [showCapacityConfig, setShowCapacityConfig] = useState(false)
  const [capacityFormData, setCapacityFormData] = useState({ total_gb: '', notes: '' })
  const [scanResults, setScanResults] = useState<ScanResults | null>(null)
  const [showRuleForm, setShowRuleForm] = useState(false)
  const [editingRule, setEditingRule] = useState<DeletionRule | null>(null)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  
  // Selection and filtering state
  const [selectedCandidates, setSelectedCandidates] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<'title' | 'days_since_added' | 'days_since_viewed' | 'file_size_mb' | 'rating'>('days_since_viewed')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterMinSize, setFilterMinSize] = useState<string>('')
  const [filterMaxSize, setFilterMaxSize] = useState<string>('')

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    enabled: false,
    dry_run_mode: true,
    grace_period_days: 30,
    inactivity_threshold_days: 15,
    excluded_genres: '',
    min_rating: ''
  })

  useEffect(() => {
    // Run auth check, rules loading, and storage info in parallel
    // BUT don't let storage info block the page from loading
    const startTime = Date.now()
    console.log('[Deletion Page] Starting initialization...')
    
    Promise.all([
      checkAuth().catch(err => console.error('Auth error:', err)),
      loadRules().catch(err => console.error('Rules error:', err)),
      loadStorageInfo().catch(err => {
        console.error('Storage info error:', err)
        // Set empty storage info so page doesn't hang
        setStorageInfo({
          total_items: 0,
          total_used_gb: 0,
          total_used_tb: 0,
          capacity_configured: false
        })
      })
    ])
      .then(() => {
        const duration = Date.now() - startTime
        console.log(`[Deletion Page] Initialization complete in ${duration}ms`)
      })
      .catch(err => {
        console.error('Init error:', err)
        setError('Failed to load page. Please refresh.')
        setLoading(false)
      })
  }, [])

  async function checkAuth() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.push('/login')
      return
    }

    // Check if user is admin
    const { data: user } = await supabase
      .from('users')
      .select('role')
      .eq('id', session.user.id)
      .single()

    if (user?.role !== 'admin') {
      router.push('/dashboard')
    }
  }

  async function loadRules() {
    // Show loading immediately
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        setLoading(false)
        return
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/rules`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        }
      )

      if (response.ok) {
        const data = await response.json()
        setRules(data)
      }
    } catch (err) {
      console.error('Error loading rules:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const body = {
        ...formData,
        excluded_genres: formData.excluded_genres ? formData.excluded_genres.split(',').map(g => g.trim()) : [],
        min_rating: formData.min_rating ? parseFloat(formData.min_rating) : null
      }

      const url = editingRule 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/rules/${editingRule.id}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/rules`

      const response = await fetch(url, {
        method: editingRule ? 'PATCH' : 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      if (response.ok) {
        setShowRuleForm(false)
        setEditingRule(null)
        setFormData({
          name: '',
          description: '',
          enabled: false,
          dry_run_mode: true,
          grace_period_days: 30,
          inactivity_threshold_days: 15,
          excluded_genres: '',
          min_rating: ''
        })
        loadRules()
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to save rule')
      }
    } catch (err) {
      setError('Failed to save rule')
      console.error(err)
    }
  }

  async function scanForCandidates(ruleId: string) {
    setScanning(true)
    setScanResults(null)
    setError('')

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/scan`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ rule_id: ruleId, dry_run: true })
        }
      )

      if (response.ok) {
        const results = await response.json()
        setScanResults(results)
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to scan for candidates')
      }
    } catch (err) {
      setError('Failed to scan for candidates')
      console.error(err)
    } finally {
      setScanning(false)
    }
  }

  async function executeDeletion(ruleId: string, dryRun: boolean = false) {
    if (!dryRun) {
      if (!scanResults || scanResults.candidates.length === 0) {
        return
      }
      
      const totalSize = scanResults.candidates.reduce((sum, c) => sum + (c.file_size_mb || 0), 0) / 1024
      
      const confirmMessage = `🚨 PERMANENT DELETION WARNING 🚨

This action is IRREVERSIBLE and will:
• Delete ${scanResults.candidates.length} file(s) from Plex library
• Remove ${totalSize.toFixed(2)} GB of content permanently
• Remove from Sonarr/Radarr (prevent re-download)
• Clear Overseerr requests

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
      if (!session) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/execute`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ rule_id: ruleId, dry_run: dryRun })
        }
      )

      if (response.ok) {
        const results = await response.json()
        const { deleted, failed, total_size_mb } = results.results
        
        if (dryRun) {
          alert(`✅ Dry Run Complete!\n\n` +
                `Would delete: ${deleted} items\n` +
                `Failed: ${failed} items\n` +
                `Space to free: ${total_size_mb.toFixed(0)} MB`)
        } else {
          alert(`✅ Deletion Complete!\n\n` +
                `Deleted: ${deleted} items\n` +
                `Failed: ${failed} items\n` +
                `Space freed: ${total_size_mb.toFixed(0)} MB`)
        }
        
        setScanResults(null)
        loadRules()
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to execute deletion')
      }
    } catch (err) {
      setError('Failed to execute deletion')
      console.error(err)
    } finally {
      setExecuting(false)
    }
  }

  async function cancelSync() {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      // Call cancel endpoint
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/plex/cancel-sync`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      })

      // Close event source
      if (syncEventSource) {
        syncEventSource.close()
        setSyncEventSource(null)
      }

      setSyncing(false)
      setSuccessMessage('Sync cancelled')
      setTimeout(() => setSuccessMessage(''), 5000)
    } catch (err) {
      console.error('Failed to cancel sync:', err)
    }
  }

  async function syncLibrary() {
    setSyncing(true)
    setError('')
    setSuccessMessage('')
    setSyncProgress({ current: 0, total: 0, eta: '', title: '', section: '', itemsPerSecond: 0 })

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      // Get Plex token from localStorage
      const plexToken = localStorage.getItem('plex_token')
      
      if (!plexToken) {
        setError('No Plex token found. Please reconnect your Plex account from the dashboard.')
        setSyncing(false)
        return
      }

      // Connect to SSE endpoint for streaming progress
      // EventSource doesn't support custom headers, so we pass auth token as query param
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL}/api/plex/sync-library-stream?plex_token=${plexToken}&auth_token=${session.access_token}`
      )
      setSyncEventSource(eventSource)

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.status === 'connecting' || data.status === 'counting') {
            setSyncProgress({ 
              current: 0, 
              total: 0, 
              eta: data.message,
              title: '',
              section: '',
              itemsPerSecond: 0
            })
          } else if (data.status === 'syncing') {
            const etaMinutes = Math.floor(data.eta_seconds / 60)
            const etaSeconds = data.eta_seconds % 60
            const etaStr = etaMinutes > 0 
              ? `${etaMinutes}m ${etaSeconds}s remaining`
              : `${etaSeconds}s remaining`
            
            setSyncProgress({
              current: data.current,
              total: data.total,
              eta: etaStr,
              title: data.title || '',
              section: data.section || '',
              itemsPerSecond: data.items_per_second || 0
            })
            
            // Update storage info in real-time if provided
            if (data.storage) {
              setStorageInfo({
                total_items: data.current, // Use current count as approximate
                total_used_gb: data.storage.total_used_gb,
                total_used_tb: parseFloat((data.storage.total_used_gb / 1024).toFixed(2)),
                total_capacity_gb: data.storage.total_capacity_gb,
                free_gb: data.storage.free_gb,
                used_percentage: data.storage.used_percentage,
                capacity_configured: data.storage.total_capacity_gb !== null,
                by_type: storageInfo?.by_type || {}
              })
            }
          } else if (data.status === 'complete') {
            setSyncProgress({
              current: data.current,
              total: data.total,
              eta: `Completed in ${data.duration_seconds}s`,
              title: '',
              section: '',
              itemsPerSecond: 0
            })
            setSuccessMessage(data.message)
            
            // Update storage from completion data
            if (data.storage) {
              setStorageInfo({
                total_items: data.current,
                total_used_gb: data.storage.total_used_gb,
                total_used_tb: parseFloat((data.storage.total_used_gb / 1024).toFixed(2)),
                total_capacity_gb: data.storage.total_capacity_gb,
                free_gb: data.storage.free_gb,
                used_percentage: data.storage.used_percentage,
                capacity_configured: data.storage.total_capacity_gb !== null,
                by_type: storageInfo?.by_type || {}
              })
            }
            
            // Close connection
            eventSource.close()
            setSyncEventSource(null)
            setSyncing(false)
            
            // Reload full storage info (with by_type breakdown) after 2 seconds
            setTimeout(() => {
              loadStorageInfo()
            }, 2000)
            
            // Clear message after 8 seconds
            setTimeout(() => {
              setSuccessMessage('')
              setSyncProgress({ current: 0, total: 0, eta: '', title: '', section: '', itemsPerSecond: 0 })
            }, 8000)
          } else if (data.status === 'error') {
            setError(data.message)
            eventSource.close()
            setSyncEventSource(null)
            setSyncing(false)
          } else if (data.status === 'cancelled') {
            setSuccessMessage('Sync cancelled by user')
            eventSource.close()
            setSyncEventSource(null)
            setSyncing(false)
            setTimeout(() => setSuccessMessage(''), 5000)
          } else if (data.status === 'warning') {
            console.warn('Sync warning:', data.message)
          }
        } catch (parseError) {
          console.error('Failed to parse SSE data:', parseError)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        setError('Sync connection lost. Please try again.')
        eventSource.close()
        setSyncEventSource(null)
        setSyncing(false)
      }
      
    } catch (err) {
      setError('Failed to start sync. Please try again.')
      console.error(err)
      setSyncing(false)
    }
  }

  async function loadStorageInfo() {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        console.warn('No session, skipping storage info load')
        return
      }

      const plexToken = localStorage.getItem('plex_token')
      if (!plexToken) {
        console.warn('No plex_token in localStorage, skipping storage info load')
        // Set empty storage info so page doesn't hang
        setStorageInfo({
          total_items: 0,
          total_used_gb: 0,
          total_used_tb: 0,
          capacity_configured: false
        })
        return
      }

      // Add timestamp to bust any caching
      const timestamp = Date.now()
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/plex/storage-info?plex_token=${plexToken}&_t=${timestamp}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
          cache: 'no-store', // Prevent browser caching
        }
      )

      if (response.ok) {
        const data = await response.json()
        setStorageInfo(data)
      } else {
        console.error('Storage info request failed:', response.status)
        // Set empty storage info on failure
        setStorageInfo({
          total_items: 0,
          total_used_gb: 0,
          total_used_tb: 0,
          capacity_configured: false
        })
      }
    } catch (err) {
      console.error('Failed to load storage info:', err)
      // Set empty storage info on error so page doesn't hang
      setStorageInfo({
        total_items: 0,
        total_used_gb: 0,
        total_used_tb: 0,
        capacity_configured: false
      })
    }
  }

  async function updateStorageCapacity() {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const totalGb = parseFloat(capacityFormData.total_gb)
      if (isNaN(totalGb) || totalGb <= 0) {
        setError('Please enter a valid capacity in GB')
        return
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/system/config/storage-capacity`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            total_gb: totalGb,
            source: 'manual',
            notes: capacityFormData.notes || 'Manually configured by admin'
          })
        }
      )

      if (response.ok) {
        setSuccessMessage('Storage capacity updated successfully!')
        setShowCapacityConfig(false)
        setCapacityFormData({ total_gb: '', notes: '' })
        loadStorageInfo()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to update storage capacity')
      }
    } catch (err) {
      console.error('Failed to update storage capacity:', err)
      setError('Failed to update storage capacity')
    }
  }

  async function deleteRule(ruleId: string, name: string) {
    if (!confirm(`Delete rule "${name}"?`)) return

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/deletion/rules/${ruleId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        }
      )

      if (response.ok) {
        loadRules()
      }
    } catch (err) {
      console.error('Error deleting rule:', err)
    }
  }

  function editRule(rule: DeletionRule) {
    setEditingRule(rule)
    setFormData({
      name: rule.name,
      description: rule.description || '',
      enabled: rule.enabled,
      dry_run_mode: rule.dry_run_mode,
      grace_period_days: rule.grace_period_days,
      inactivity_threshold_days: rule.inactivity_threshold_days,
      excluded_genres: rule.excluded_genres.join(', '),
      min_rating: rule.min_rating?.toString() || ''
    })
    setShowRuleForm(true)
  }

  const formatFileSize = (mb: number | null) => {
    if (!mb) return 'Unknown'
    if (mb < 1024) return `${mb.toFixed(0)} MB`
    return `${(mb / 1024).toFixed(2)} GB`
  }

  // Format title with show/season/episode info for TV episodes
  const formatTitle = (candidate: DeletionCandidate) => {
    if (candidate.type === 'episode' && candidate.parent_title) {
      const season = candidate.season_number ? `S${candidate.season_number.toString().padStart(2, '0')}` : 'S??'
      const episode = candidate.episode_number ? `E${candidate.episode_number.toString().padStart(2, '0')}` : 'E??'
      return `${candidate.parent_title} - ${season}${episode} - ${candidate.title}`
    }
    return candidate.title
  }

  // Get filtered and sorted candidates
  const getFilteredAndSortedCandidates = () => {
    if (!scanResults) return []
    
    let filtered = scanResults.candidates
    
    // Filter by type
    if (filterType !== 'all') {
      filtered = filtered.filter(c => c.type === filterType)
    }
    
    // Filter by size
    if (filterMinSize) {
      const minMB = parseFloat(filterMinSize) * 1024 // Convert GB to MB
      filtered = filtered.filter(c => (c.file_size_mb || 0) >= minMB)
    }
    if (filterMaxSize) {
      const maxMB = parseFloat(filterMaxSize) * 1024 // Convert GB to MB
      filtered = filtered.filter(c => (c.file_size_mb || 0) <= maxMB)
    }
    
    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any = a[sortBy]
      let bVal: any = b[sortBy]
      
      // Handle nulls
      if (aVal === null || aVal === undefined) aVal = sortBy === 'rating' ? 0 : 999999
      if (bVal === null || bVal === undefined) bVal = sortBy === 'rating' ? 0 : 999999
      
      // Handle strings (title)
      if (sortBy === 'title') {
        return sortDirection === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }
      
      // Handle numbers
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })
    
    return sorted
  }

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      // Toggle direction
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortDirection('desc')
    }
  }

  const toggleSelectCandidate = (id: string) => {
    const newSelected = new Set(selectedCandidates)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedCandidates(newSelected)
  }

  const toggleSelectAll = () => {
    const filtered = getFilteredAndSortedCandidates()
    if (selectedCandidates.size === filtered.length) {
      // Deselect all
      setSelectedCandidates(new Set())
    } else {
      // Select all filtered
      setSelectedCandidates(new Set(filtered.map(c => c.id)))
    }
  }

  // Get unique TV shows from candidates
  const getTVShows = () => {
    if (!scanResults) return []
    const shows = new Map<string, { name: string, count: number, ids: string[] }>()
    
    scanResults.candidates
      .filter(c => c.type === 'episode' && c.parent_title)
      .forEach(c => {
        const showName = c.parent_title!
        if (!shows.has(showName)) {
          shows.set(showName, { name: showName, count: 0, ids: [] })
        }
        const show = shows.get(showName)!
        show.count++
        show.ids.push(c.id)
      })
    
    return Array.from(shows.values()).sort((a, b) => b.count - a.count)
  }

  const selectAllFromShow = (showName: string) => {
    const filtered = getFilteredAndSortedCandidates()
    const showEpisodes = filtered
      .filter(c => c.type === 'episode' && c.parent_title === showName)
      .map(c => c.id)
    
    const newSelected = new Set(selectedCandidates)
    showEpisodes.forEach(id => newSelected.add(id))
    setSelectedCandidates(newSelected)
  }

  const deselectAllFromShow = (showName: string) => {
    const filtered = getFilteredAndSortedCandidates()
    const showEpisodes = filtered
      .filter(c => c.type === 'episode' && c.parent_title === showName)
      .map(c => c.id)
    
    const newSelected = new Set(selectedCandidates)
    showEpisodes.forEach(id => newSelected.delete(id))
    setSelectedCandidates(newSelected)
  }

  const deleteSelected = async (dryRun: boolean = false) => {
    if (selectedCandidates.size === 0) {
      alert('Please select at least one item to delete')
      return
    }

    if (!dryRun) {
      // Calculate total size of selected items
      const selectedSize = getFilteredAndSortedCandidates()
        .filter(c => selectedCandidates.has(c.id))
        .reduce((sum, c) => sum + (c.file_size_mb || 0), 0) / 1024
      
      const confirmMessage = `🚨 PERMANENT DELETION WARNING 🚨

This action is IRREVERSIBLE and will:
• Delete ${selectedCandidates.size} file(s) from Plex library
• Remove ${selectedSize.toFixed(2)} GB of content permanently
• Remove from Sonarr/Radarr (prevent re-download)
• Clear Overseerr requests

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

      const response = await fetch(
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
            candidate_ids: Array.from(selectedCandidates)
          })
        }
      )

      if (response.ok) {
        const results = await response.json()
        const { deleted, failed, total_size_mb } = results.results
        
        if (dryRun) {
          alert(`✅ Dry Run Complete!\n\n` +
                `Would delete: ${deleted} items\n` +
                `Failed: ${failed} items\n` +
                `Space to free: ${(total_size_mb / 1024).toFixed(2)} GB`)
        } else {
          alert(`✅ Deletion Complete!\n\n` +
                `Deleted: ${deleted} items\n` +
                `Failed: ${failed} items\n` +
                `Space freed: ${(total_size_mb / 1024).toFixed(2)} GB`)
        }
        
        // Clear selection and rescan
        setSelectedCandidates(new Set())
        setScanResults(null)
        loadRules()
        loadStorageInfo()
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to execute deletion')
      }
    } catch (err) {
      setError('Failed to execute deletion')
      console.error(err)
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Library Deletion Management</h1>
            <p className="text-slate-400">Intelligently clean up unwatched content with grace periods</p>
          </div>
          <div className="flex gap-3">
            {syncing ? (
              <button
                onClick={cancelSync}
                className="bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
              >
                ⏹ Cancel Sync
              </button>
            ) : (
              <button
                onClick={syncLibrary}
                disabled={syncing}
                className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
              >
                {syncing ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Syncing...
                  </>
                ) : (
                  <>
                    🔄 Sync Library
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => setShowRuleForm(true)}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              + Create Rule
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="bg-green-900/50 border border-green-500 rounded-lg p-4 mb-6">
            {successMessage}
          </div>
        )}

        {/* Storage Info Display */}
        {storageInfo && (
          <div className="bg-slate-800 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold mb-1">💾 Media Library Storage</h3>
                <p className="text-slate-400 text-sm">
                  {storageInfo.total_items.toLocaleString()} items
                  {!storageInfo.capacity_configured && (
                    <span className="text-yellow-500 ml-2">⚠️ Total capacity not configured</span>
                  )}
                </p>
              </div>
              <div className="text-right flex items-center gap-4">
                {storageInfo.capacity_configured && storageInfo.total_capacity_gb && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{storageInfo.free_gb?.toFixed(0)} GB</div>
                    <div className="text-slate-400 text-xs">Free Space</div>
                  </div>
                )}
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-400">{storageInfo.total_used_tb.toFixed(2)} TB</div>
                  <div className="text-slate-400 text-sm">
                    {storageInfo.total_used_gb.toFixed(0)} GB used
                    {storageInfo.capacity_configured && storageInfo.total_capacity_gb && (
                      <span className="ml-1">
                        of {(storageInfo.total_capacity_gb / 1024).toFixed(2)} TB ({storageInfo.used_percentage?.toFixed(1)}%)
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setShowCapacityConfig(true)}
                  className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
                  title="Configure total capacity"
                >
                  ⚙️
                </button>
              </div>
            </div>
            
            {/* Progress bar if capacity configured */}
            {storageInfo.capacity_configured && storageInfo.used_percentage && (
              <div className="mb-4">
                <div className="w-full bg-slate-700 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full transition-all ${
                      storageInfo.used_percentage > 90 ? 'bg-red-500' :
                      storageInfo.used_percentage > 75 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(storageInfo.used_percentage, 100)}%` }}
                  />
                </div>
              </div>
            )}
            
            {/* Breakdown by type */}
            {storageInfo.by_type && Object.keys(storageInfo.by_type).length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {Object.entries(storageInfo.by_type).map(([type, stats]: [string, any]) => (
                  <div key={type} className="bg-slate-700/50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 uppercase mb-1">{type}</div>
                    <div className="text-lg font-semibold">{stats.count.toLocaleString()}</div>
                    <div className="text-xs text-slate-500">{stats.size_gb.toFixed(1)} GB</div>
                  </div>
                ))}
              </div>
            )}
            
            {scanResults && scanResults.candidates.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">💡 Space that could be freed:</span>
                  <span className="text-green-400 font-semibold">
                    {(scanResults.candidates.reduce((sum, c) => sum + (c.file_size_mb || 0), 0) / 1024).toFixed(2)} GB
                    ({((scanResults.candidates.reduce((sum, c) => sum + (c.file_size_mb || 0), 0) / 1024) / storageInfo.total_used_gb * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sync Progress Indicator - Enhanced */}
        {syncing && syncProgress.current > 0 && (
          <div className="bg-purple-900/30 border border-purple-500/50 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <svg className="animate-spin h-5 w-5 text-purple-400" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <div className="flex flex-col">
                  <span className="text-purple-300 font-medium">
                    Syncing Library: {syncProgress.current.toLocaleString()} / {syncProgress.total.toLocaleString()} items
                  </span>
                  {syncProgress.title && (
                    <span className="text-purple-400 text-sm">
                      📺 {syncProgress.section}: {syncProgress.title}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-purple-400 text-sm font-medium">{syncProgress.eta}</div>
                {syncProgress.itemsPerSecond > 0 && (
                  <div className="text-purple-500 text-xs">⚡ {syncProgress.itemsPerSecond.toFixed(1)} items/sec</div>
                )}
              </div>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2.5">
              <div 
                className="bg-gradient-to-r from-purple-500 to-purple-400 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${syncProgress.total > 0 ? Math.min((syncProgress.current / syncProgress.total) * 100, 100) : 0}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>{syncProgress.total > 0 ? Math.min((syncProgress.current / syncProgress.total) * 100, 100).toFixed(1) : 0}%</span>
              <span>{Math.max(syncProgress.total - syncProgress.current, 0)} remaining</span>
            </div>
          </div>
        )}
        
        {syncing && syncProgress.current === 0 && (
          <div className="bg-purple-900/30 border border-purple-500/50 rounded-lg p-6 mb-6">
            <div className="flex items-center gap-3">
              <svg className="animate-spin h-5 w-5 text-purple-400" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-purple-300 font-medium">{syncProgress.eta}</span>
            </div>
          </div>
        )}

        {/* Rule Form Modal */}
        {showRuleForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
            <div className="bg-slate-800 rounded-lg p-8 max-w-2xl w-full my-8">
              <h2 className="text-2xl font-bold mb-6">
                {editingRule ? 'Edit' : 'Create'} Deletion Rule
              </h2>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Rule Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="Default Cleanup Rule"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 h-20"
                    placeholder="Removes media that hasn't been watched recently..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Grace Period (days)
                      <span className="text-slate-400 text-xs ml-2">Min days since added</span>
                    </label>
                    <input
                      type="number"
                      value={formData.grace_period_days}
                      onChange={(e) => setFormData({ ...formData, grace_period_days: parseInt(e.target.value) })}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                      min="0"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Inactivity Threshold (days)
                      <span className="text-slate-400 text-xs ml-2">Days not watched</span>
                    </label>
                    <input
                      type="number"
                      value={formData.inactivity_threshold_days}
                      onChange={(e) => setFormData({ ...formData, inactivity_threshold_days: parseInt(e.target.value) })}
                      className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                      min="0"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Excluded Genres (comma separated)
                  </label>
                  <input
                    type="text"
                    value={formData.excluded_genres}
                    onChange={(e) => setFormData({ ...formData, excluded_genres: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="Documentary, Kids, Animation"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Minimum Rating (optional)
                    <span className="text-slate-400 text-xs ml-2">Only delete items below this rating</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.min_rating}
                    onChange={(e) => setFormData({ ...formData, min_rating: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="7.0"
                    min="0"
                    max="10"
                  />
                </div>

                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">Enable this rule</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.dry_run_mode}
                      onChange={(e) => setFormData({ ...formData, dry_run_mode: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">Dry run mode (safe, no actual deletions)</span>
                  </label>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 hover:bg-blue-700 py-2 rounded font-semibold transition-colors"
                  >
                    {editingRule ? 'Update' : 'Create'} Rule
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowRuleForm(false)
                      setEditingRule(null)
                      setError('')
                    }}
                    className="flex-1 bg-slate-700 hover:bg-slate-600 py-2 rounded font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Rules List */}
        {rules.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-12 text-center">
            <div className="text-6xl mb-4">🗑️</div>
            <h3 className="text-xl font-semibold mb-2">No Deletion Rules</h3>
            <p className="text-slate-400 mb-6">
              Create your first rule to start managing library cleanup
            </p>
          </div>
        ) : (
          <div className="grid gap-6">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="bg-slate-800 rounded-lg p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold">{rule.name}</h3>
                      {rule.enabled && (
                        <span className="bg-green-600 text-xs px-2 py-1 rounded">ENABLED</span>
                      )}
                      {rule.dry_run_mode && (
                        <span className="bg-yellow-600 text-xs px-2 py-1 rounded">DRY RUN</span>
                      )}
                    </div>
                    {rule.description && (
                      <p className="text-slate-400 text-sm mb-3">{rule.description}</p>
                    )}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500">Grace Period:</span>
                        <span className="ml-2 font-medium">{rule.grace_period_days} days</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Inactivity:</span>
                        <span className="ml-2 font-medium">{rule.inactivity_threshold_days} days</span>
                      </div>
                      {rule.min_rating && (
                        <div>
                          <span className="text-slate-500">Min Rating:</span>
                          <span className="ml-2 font-medium">{rule.min_rating}</span>
                        </div>
                      )}
                      {rule.last_run_at && (
                        <div>
                          <span className="text-slate-500">Last Run:</span>
                          <span className="ml-2 font-medium">
                            {new Date(rule.last_run_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => scanForCandidates(rule.id)}
                      disabled={scanning}
                      className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm font-medium transition-colors"
                    >
                      {scanning ? 'Scanning...' : 'Scan'}
                    </button>
                    <button
                      onClick={() => editRule(rule)}
                      className="bg-slate-600 hover:bg-slate-700 px-4 py-2 rounded text-sm font-medium transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id, rule.name)}
                      className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded text-sm font-medium transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Scan Results */}
        {scanResults && (
          <div className="mt-8 bg-slate-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold">Deletion Candidates</h3>
                <p className="text-slate-400">
                  Found {scanResults.total_candidates} items • {selectedCandidates.size} selected
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => deleteSelected(true)}
                  disabled={executing || selectedCandidates.size === 0}
                  className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-800 disabled:cursor-not-allowed px-6 py-2 rounded font-semibold transition-colors"
                >
                  {executing ? 'Processing...' : `Dry Run (${selectedCandidates.size})`}
                </button>
                <button
                  onClick={() => deleteSelected(false)}
                  disabled={executing || selectedCandidates.size === 0}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:cursor-not-allowed px-6 py-2 rounded font-semibold transition-colors"
                >
                  {executing ? 'Processing...' : `⚠️ Delete (${selectedCandidates.size})`}
                </button>
              </div>
            </div>

            {/* Filters and Controls */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 p-4 bg-slate-700/50 rounded-lg">
              <div>
                <label className="block text-xs font-medium mb-1 text-slate-400">Type</label>
                <select 
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="movie">Movies</option>
                  <option value="show">TV Shows</option>
                  <option value="season">Seasons</option>
                  <option value="episode">Episodes</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs font-medium mb-1 text-slate-400">Min Size (GB)</label>
                <input
                  type="number"
                  step="0.1"
                  value={filterMinSize}
                  onChange={(e) => setFilterMinSize(e.target.value)}
                  placeholder="0"
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              </div>
              
              <div>
                <label className="block text-xs font-medium mb-1 text-slate-400">Max Size (GB)</label>
                <input
                  type="number"
                  step="0.1"
                  value={filterMaxSize}
                  onChange={(e) => setFilterMaxSize(e.target.value)}
                  placeholder="100"
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              </div>
              
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setFilterType('all')
                    setFilterMinSize('')
                    setFilterMaxSize('')
                  }}
                  className="w-full bg-slate-600 hover:bg-slate-500 px-4 py-2 rounded text-sm font-medium transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            </div>

            {/* TV Show Bulk Selection */}
            {getTVShows().length > 0 && (
              <div className="mb-6 p-4 bg-slate-700/50 rounded-lg">
                <h4 className="text-sm font-semibold mb-3 text-slate-300">📺 Select by TV Show</h4>
                <div className="flex flex-wrap gap-2">
                  {getTVShows().map(show => {
                    const filtered = getFilteredAndSortedCandidates()
                    const showEpisodes = filtered.filter(c => c.type === 'episode' && c.parent_title === show.name)
                    const allSelected = showEpisodes.every(ep => selectedCandidates.has(ep.id))
                    const someSelected = showEpisodes.some(ep => selectedCandidates.has(ep.id)) && !allSelected
                    
                    return (
                      <button
                        key={show.name}
                        onClick={() => allSelected ? deselectAllFromShow(show.name) : selectAllFromShow(show.name)}
                        className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                          allSelected 
                            ? 'bg-purple-600 hover:bg-purple-700 text-white' 
                            : someSelected
                            ? 'bg-purple-900/50 hover:bg-purple-800 text-purple-200 border border-purple-500'
                            : 'bg-slate-600 hover:bg-slate-500 text-slate-200'
                        }`}
                      >
                        {show.name} ({showEpisodes.length})
                        {allSelected && ' ✓'}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {scanResults.candidates.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-700">
                    <tr>
                      <th className="text-left p-3">
                        <input
                          type="checkbox"
                          checked={selectedCandidates.size === getFilteredAndSortedCandidates().length && selectedCandidates.size > 0}
                          onChange={toggleSelectAll}
                          className="w-4 h-4 cursor-pointer"
                        />
                      </th>
                      <th 
                        className="text-left p-3 cursor-pointer hover:bg-slate-600"
                        onClick={() => handleSort('title')}
                      >
                        Title {sortBy === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th className="text-left p-3">Type</th>
                      <th 
                        className="text-right p-3 cursor-pointer hover:bg-slate-600"
                        onClick={() => handleSort('days_since_added')}
                      >
                        Days Old {sortBy === 'days_since_added' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th 
                        className="text-right p-3 cursor-pointer hover:bg-slate-600"
                        onClick={() => handleSort('days_since_viewed')}
                      >
                        Days Unwatched {sortBy === 'days_since_viewed' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th className="text-right p-3">Views</th>
                      <th 
                        className="text-right p-3 cursor-pointer hover:bg-slate-600"
                        onClick={() => handleSort('rating')}
                      >
                        Rating {sortBy === 'rating' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th 
                        className="text-right p-3 cursor-pointer hover:bg-slate-600"
                        onClick={() => handleSort('file_size_mb')}
                      >
                        Size {sortBy === 'file_size_mb' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {getFilteredAndSortedCandidates().map((candidate) => (
                      <tr 
                        key={candidate.id} 
                        className={`border-t border-slate-700 hover:bg-slate-750 transition-colors ${
                          selectedCandidates.has(candidate.id) ? 'bg-purple-900/20' : ''
                        }`}
                      >
                        <td className="p-3">
                          <input
                            type="checkbox"
                            checked={selectedCandidates.has(candidate.id)}
                            onChange={() => toggleSelectCandidate(candidate.id)}
                            className="w-4 h-4 cursor-pointer"
                          />
                        </td>
                        <td className="p-3 font-medium">{formatTitle(candidate)}</td>
                        <td className="p-3 text-slate-400">{candidate.type}</td>
                        <td className="p-3 text-right">{candidate.days_since_added}d</td>
                        <td className="p-3 text-right text-yellow-400">{candidate.days_since_viewed}d</td>
                        <td className="p-3 text-right">{candidate.view_count}</td>
                        <td className="p-3 text-right">
                          {candidate.rating ? candidate.rating.toFixed(1) : 'N/A'}
                        </td>
                        <td className="p-3 text-right text-slate-400">
                          {formatFileSize(candidate.file_size_mb)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {/* Summary Footer */}
                <div className="mt-4 pt-4 border-t border-slate-700 flex justify-between text-sm">
                  <div className="text-slate-400">
                    Showing {getFilteredAndSortedCandidates().length} of {scanResults.candidates.length} items
                  </div>
                  {selectedCandidates.size > 0 && (
                    <div className="text-purple-400 font-medium">
                      Selected: {selectedCandidates.size} items • {
                        (getFilteredAndSortedCandidates()
                          .filter(c => selectedCandidates.has(c.id))
                          .reduce((sum, c) => sum + (c.file_size_mb || 0), 0) / 1024
                        ).toFixed(2)
                      } GB
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-center text-slate-400 py-8">No candidates found</p>
            )}
          </div>
        )}
        
        {/* Storage Capacity Configuration Modal */}
        {showCapacityConfig && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-8 max-w-md w-full">
              <h2 className="text-2xl font-bold mb-6">Configure Storage Capacity</h2>
              
              {storageInfo && (
                <div className="mb-6 p-4 bg-slate-700/50 rounded">
                  <div className="text-sm text-slate-400 mb-2">Current Usage</div>
                  <div className="text-2xl font-bold text-purple-400">{storageInfo.total_used_tb.toFixed(2)} TB</div>
                  <div className="text-sm text-slate-500">{storageInfo.total_used_gb.toFixed(0)} GB used</div>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Total Capacity (GB)</label>
                  <input
                    type="number"
                    step="100"
                    value={capacityFormData.total_gb}
                    onChange={(e) => setCapacityFormData({ ...capacityFormData, total_gb: e.target.value })}
                    placeholder="e.g., 10000 for 10TB"
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Enter your total storage capacity in gigabytes
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Notes (optional)</label>
                  <input
                    type="text"
                    value={capacityFormData.notes}
                    onChange={(e) => setCapacityFormData({ ...capacityFormData, notes: e.target.value })}
                    placeholder="e.g., Ultra.cc 10TB plan"
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                  />
                </div>
                
                {capacityFormData.total_gb && (
                  <div className="p-3 bg-blue-900/30 border border-blue-500/50 rounded text-sm">
                    <div className="text-blue-300 mb-1">Preview:</div>
                    <div className="text-slate-300">
                      Total: {(parseFloat(capacityFormData.total_gb) / 1024).toFixed(2)} TB
                    </div>
                    {storageInfo && (
                      <>
                        <div className="text-slate-300">
                          Used: {storageInfo.total_used_tb.toFixed(2)} TB ({((storageInfo.total_used_gb / parseFloat(capacityFormData.total_gb)) * 100).toFixed(1)}%)
                        </div>
                        <div className="text-green-400">
                          Free: {((parseFloat(capacityFormData.total_gb) - storageInfo.total_used_gb) / 1024).toFixed(2)} TB
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowCapacityConfig(false)
                    setCapacityFormData({ total_gb: '', notes: '' })
                  }}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={updateStorageCapacity}
                  disabled={!capacityFormData.total_gb}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Save Capacity
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
