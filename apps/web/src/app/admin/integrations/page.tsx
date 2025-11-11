'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { Database } from '@smartplex/db'

interface Integration {
  id: string
  service: string
  name: string
  url: string
  status: string
  last_sync_at: string | null
  created_at: string
  updated_at: string
  config: any
}

export default function IntegrationsPage() {
  const router = useRouter()
  const [supabase] = useState(() => createClientComponentClient<Database>())
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [syncingTautulli, setSyncingTautulli] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Form state
  const [formData, setFormData] = useState({
    service: 'tautulli',
    name: '',
    url: '',
    api_key: ''
  })

  useEffect(() => {
    checkAuth()
    loadIntegrations()
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

  async function loadIntegrations() {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        console.error('❌ NEXT_PUBLIC_API_URL is not set')
        setLoading(false)
        return
      }

      const response = await fetch(
        `${apiUrl}/api/integrations`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        }
      )

      if (response.ok) {
        const data = await response.json()
        setIntegrations(data)
      } else {
        console.error('Failed to load integrations:', response.status, response.statusText)
      }
    } catch (err) {
      console.error('Error loading integrations:', err)
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

      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        setError('API URL not configured. Please set NEXT_PUBLIC_API_URL in Vercel environment variables.')
        console.error('❌ NEXT_PUBLIC_API_URL is not set')
        return
      }

      const response = await fetch(
        `${apiUrl}/api/integrations`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData)
        }
      )

      console.log('Integration create response:', response.status, response.statusText)

      if (response.ok) {
        setShowAddForm(false)
        setFormData({ service: 'tautulli', name: '', url: '', api_key: '' })
        loadIntegrations()
      } else {
        const error = await response.json()
        console.error('Integration create error:', error)
        setError(error.detail || `Failed to create integration: ${response.status}`)
      }
    } catch (err) {
      console.error('Integration creation exception:', err)
      setError(`Failed to create integration: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  async function testConnection(id: string) {
    setTestingId(id)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/integrations/${id}/test`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        }
      )

      const result = await response.json()
      
      if (result.success) {
        alert(`✅ Connection successful!\n\nService: ${result.details.service}\nResponse time: ${result.details.response_time_ms.toFixed(0)}ms`)
      } else {
        alert(`❌ Connection failed:\n\n${result.error}`)
      }

      // Reload to get updated status
      loadIntegrations()
    } catch (err) {
      alert('Failed to test connection')
      console.error(err)
    } finally {
      setTestingId(null)
    }
  }

  const [tautulliSyncProgress, setTautulliSyncProgress] = useState({ current: 0, total: 0, eta: '', itemsPerSecond: 0, updated: 0, created: 0 })
  const [tautulliSyncEventSource, setTautulliSyncEventSource] = useState<EventSource | null>(null)

  async function syncTautulliData(days: number = 90) {
    setSyncingTautulli(true)
    setError('')
    setSuccessMessage('')
    setTautulliSyncProgress({ current: 0, total: 0, eta: '', itemsPerSecond: 0, updated: 0, created: 0 })

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      // Use streaming endpoint for real-time progress
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sync/tautulli/stream?days_back=${days}&auth_token=${session.access_token}`
      )
      setTautulliSyncEventSource(eventSource)

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.status === 'connecting' || data.status === 'counting') {
            setTautulliSyncProgress({ 
              current: 0, 
              total: 0, 
              eta: data.message,
              itemsPerSecond: 0,
              updated: 0,
              created: 0
            })
          } else if (data.status === 'syncing') {
            const etaMinutes = Math.floor(data.eta_seconds / 60)
            const etaSeconds = data.eta_seconds % 60
            const etaStr = etaMinutes > 0 
              ? `${etaMinutes}m ${etaSeconds}s remaining`
              : `${etaSeconds}s remaining`
            
            setTautulliSyncProgress({
              current: data.current,
              total: data.total,
              eta: etaStr,
              itemsPerSecond: data.items_per_second || 0,
              updated: data.updated || 0,
              created: data.created || 0
            })
          } else if (data.status === 'complete') {
            setTautulliSyncProgress({
              current: data.current,
              total: data.total,
              eta: `Completed in ${data.duration_seconds}s`,
              itemsPerSecond: 0,
              updated: data.updated || 0,
              created: data.created || 0
            })
            setSuccessMessage(data.message)
            
            // Close connection
            eventSource.close()
            setTautulliSyncEventSource(null)
            setSyncingTautulli(false)
            
            // Reload integrations to update last_sync_at
            setTimeout(() => {
              loadIntegrations()
              setSuccessMessage('')
              setTautulliSyncProgress({ current: 0, total: 0, eta: '', itemsPerSecond: 0, updated: 0, created: 0 })
            }, 5000)
          } else if (data.status === 'error') {
            setError(data.message)
            eventSource.close()
            setTautulliSyncEventSource(null)
            setSyncingTautulli(false)
          }
        } catch (parseError) {
          console.error('Failed to parse SSE data:', parseError)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        setError('Sync connection lost. Please try again.')
        eventSource.close()
        setTautulliSyncEventSource(null)
        setSyncingTautulli(false)
      }
      
    } catch (err) {
      setError('Failed to start sync. Please try again.')
      console.error(err)
      setSyncingTautulli(false)
    }
  }

  async function cancelTautulliSync() {
    if (tautulliSyncEventSource) {
      tautulliSyncEventSource.close()
      setTautulliSyncEventSource(null)
    }
    setSyncingTautulli(false)
    setSuccessMessage('Tautulli sync cancelled')
    setTimeout(() => setSuccessMessage(''), 3000)
  }

  async function deleteIntegration(id: string, name: string) {
    if (!confirm(`Delete integration "${name}"?`)) return

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/integrations/${id}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        }
      )

      if (response.ok) {
        loadIntegrations()
      }
    } catch (err) {
      console.error('Error deleting integration:', err)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-400'
      case 'error': return 'text-red-400'
      default: return 'text-yellow-400'
    }
  }

  const getServiceIcon = (service: string) => {
    const icons: Record<string, string> = {
      tautulli: '📊',
      sonarr: '📺',
      radarr: '🎬',
      overseerr: '🎭'
    }
    return icons[service] || '🔌'
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
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Integration Management</h1>
            <p className="text-slate-400">Connect and manage external services</p>
          </div>
          <button
            onClick={() => setShowAddForm(true)}
            className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            + Add Integration
          </button>
        </div>

        {/* Add Integration Form */}
        {showAddForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg p-8 max-w-md w-full">
              <h2 className="text-2xl font-bold mb-6">Add Integration</h2>
              
              {error && (
                <div className="bg-red-900/50 border border-red-500 rounded p-3 mb-4 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Service</label>
                  <select
                    value={formData.service}
                    onChange={(e) => setFormData({ ...formData, service: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    required
                  >
                    <option value="tautulli">Tautulli</option>
                    <option value="sonarr">Sonarr</option>
                    <option value="radarr">Radarr</option>
                    <option value="overseerr">Overseerr</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="My Tautulli Instance"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">URL</label>
                  <input
                    type="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="http://192.168.1.100:8181"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">API Key</label>
                  <input
                    type="password"
                    value={formData.api_key}
                    onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2"
                    placeholder="Your API key"
                    required
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 hover:bg-blue-700 py-2 rounded font-semibold transition-colors"
                  >
                    Add Integration
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddForm(false)
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

        {/* Integrations List */}
        {integrations.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-12 text-center">
            <div className="text-6xl mb-4">🔌</div>
            <h3 className="text-xl font-semibold mb-2">No Integrations Yet</h3>
            <p className="text-slate-400 mb-6">
              Connect your first service to start managing your media library
            </p>
            <button
              onClick={() => setShowAddForm(true)}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold transition-colors"
            >
              Add Your First Integration
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {integrations.map((integration) => (
              <div
                key={integration.id}
                className="bg-slate-800 rounded-lg p-6 hover:bg-slate-750 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-4xl">{getServiceIcon(integration.service)}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold">{integration.name}</h3>
                        <span className={`text-sm font-medium ${getStatusColor(integration.status)}`}>
                          ● {integration.status}
                        </span>
                      </div>
                      <p className="text-slate-400 text-sm mb-2">{integration.url}</p>
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>Service: {integration.service}</span>
                        {integration.last_sync_at && (
                          <span>Last sync: {new Date(integration.last_sync_at).toLocaleString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => testConnection(integration.id)}
                      disabled={testingId === integration.id}
                      className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm font-medium transition-colors"
                    >
                      {testingId === integration.id ? 'Testing...' : 'Test'}
                    </button>
                    <button
                      onClick={() => deleteIntegration(integration.id, integration.name)}
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

        {/* Tautulli Data Sync Section */}
        {integrations.some(i => i.service === 'tautulli' && i.status === 'active') && (
          <div className="bg-slate-800 rounded-lg p-6 mt-6">
            <h3 className="text-xl font-semibold mb-4">Tautulli Watch History Sync</h3>
            <p className="text-slate-400 text-sm mb-4">
              Sync watch statistics from Tautulli to enable intelligent deletion decisions.
              This populates play counts, last watched dates, and watch durations for all media items.
            </p>
            
            {/* Sync Progress Indicator */}
            {syncingTautulli && tautulliSyncProgress.current > 0 && (
              <div className="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <svg className="animate-spin h-5 w-5 text-blue-400" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <div className="flex flex-col">
                      <span className="text-blue-300 font-medium">
                        Syncing History: {tautulliSyncProgress.current.toLocaleString()} / {tautulliSyncProgress.total.toLocaleString()} items
                      </span>
                      <span className="text-blue-400 text-sm">
                        Updated: {tautulliSyncProgress.updated} • Created: {tautulliSyncProgress.created}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-blue-400 text-sm font-medium">{tautulliSyncProgress.eta}</div>
                    {tautulliSyncProgress.itemsPerSecond > 0 && (
                      <div className="text-blue-500 text-xs">⚡ {tautulliSyncProgress.itemsPerSecond.toFixed(1)} items/sec</div>
                    )}
                  </div>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2.5">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-blue-400 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${tautulliSyncProgress.total > 0 ? Math.min((tautulliSyncProgress.current / tautulliSyncProgress.total) * 100, 100) : 0}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>{tautulliSyncProgress.total > 0 ? Math.min((tautulliSyncProgress.current / tautulliSyncProgress.total) * 100, 100).toFixed(1) : 0}%</span>
                  <span>{Math.max(tautulliSyncProgress.total - tautulliSyncProgress.current, 0)} remaining</span>
                </div>
                <button
                  onClick={cancelTautulliSync}
                  className="mt-3 w-full bg-red-600 hover:bg-red-700 px-4 py-2 rounded text-sm font-medium transition-colors"
                >
                  Cancel Sync
                </button>
              </div>
            )}
            
            {syncingTautulli && tautulliSyncProgress.current === 0 && (
              <div className="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-3">
                  <svg className="animate-spin h-5 w-5 text-blue-400" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-blue-300 font-medium">{tautulliSyncProgress.eta}</span>
                </div>
              </div>
            )}
            
            {successMessage && (
              <div className="bg-green-900/50 border border-green-500 rounded p-3 mb-4 text-sm whitespace-pre-line">
                {successMessage}
              </div>
            )}
            
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded p-3 mb-4 text-sm">
                {error}
              </div>
            )}
            
            <div className="flex gap-3">
              <button
                onClick={() => syncTautulliData(30)}
                disabled={syncingTautulli}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                {syncingTautulli ? 'Syncing...' : 'Sync Last 30 Days'}
              </button>
              <button
                onClick={() => syncTautulliData(90)}
                disabled={syncingTautulli}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                {syncingTautulli ? 'Syncing...' : 'Sync Last 90 Days'}
              </button>
              <button
                onClick={() => syncTautulliData(365)}
                disabled={syncingTautulli}
                className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:cursor-not-allowed px-4 py-2 rounded text-sm font-medium transition-colors"
              >
                {syncingTautulli ? 'Syncing...' : 'Sync Last Year'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
