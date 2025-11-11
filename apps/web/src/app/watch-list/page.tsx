'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { Database } from '@smartplex/db'

interface WatchListItem {
  id: string
  user_id: string
  media_item_id: string | null
  tmdb_id: number | null
  title: string
  media_type: 'movie' | 'series'
  notes: string | null
  priority: 'low' | 'medium' | 'high'
  added_at: string
  watched_at: string | null
  media_item?: {
    plex_id: string
    title: string
    type: string
    year: number | null
    poster_url: string | null
    file_size_bytes: number | null
  } | null
}

export default function WatchListPage() {
  const router = useRouter()
  const [supabase] = useState(() => createClientComponentClient<Database>())
  const [watchList, setWatchList] = useState<WatchListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState<'all' | 'unwatched' | 'watched'>('unwatched')
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'low' | 'medium' | 'high'>('all')
  const [typeFilter, setTypeFilter] = useState<'all' | 'movie' | 'series'>('all')
  const [showAddForm, setShowAddForm] = useState(false)
  const [addFormData, setAddFormData] = useState({
    title: '',
    media_type: 'movie' as 'movie' | 'series',
    notes: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
    tmdb_id: ''
  })

  useEffect(() => {
    checkAuth()
    loadWatchList()
  }, [])

  const checkAuth = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      router.push('/login')
      return
    }
  }

  const loadWatchList = async () => {
    try {
      setLoading(true)
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch('/api/watch-list', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to load watch list')
      }

      const data = await response.json()
      setWatchList(data)
    } catch (err) {
      console.error('Error loading watch list:', err)
      setError('Failed to load watch list')
    } finally {
      setLoading(false)
    }
  }

  const handleAddItem = async () => {
    if (!addFormData.title.trim()) {
      setError('Title is required')
      return
    }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch('/api/watch-list', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: addFormData.title,
          media_type: addFormData.media_type,
          notes: addFormData.notes || null,
          priority: addFormData.priority,
          tmdb_id: addFormData.tmdb_id ? parseInt(addFormData.tmdb_id) : null
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to add item')
      }

      // Reset form and reload
      setAddFormData({
        title: '',
        media_type: 'movie',
        notes: '',
        priority: 'medium',
        tmdb_id: ''
      })
      setShowAddForm(false)
      await loadWatchList()
    } catch (err) {
      console.error('Error adding item:', err)
      setError(err instanceof Error ? err.message : 'Failed to add item')
    }
  }

  const handleMarkWatched = async (itemId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch(`/api/watch-list/${itemId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          watched_at: new Date().toISOString()
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to update item')
      }

      await loadWatchList()
    } catch (err) {
      console.error('Error marking watched:', err)
      setError('Failed to mark as watched')
    }
  }

  const handleDelete = async (itemId: string) => {
    if (!confirm('Remove this item from your watch list?')) {
      return
    }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch(`/api/watch-list/${itemId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to delete item')
      }

      await loadWatchList()
    } catch (err) {
      console.error('Error deleting item:', err)
      setError('Failed to delete item')
    }
  }

  const filteredItems = watchList.filter(item => {
    if (filter === 'watched' && !item.watched_at) return false
    if (filter === 'unwatched' && item.watched_at) return false
    if (priorityFilter !== 'all' && item.priority !== priorityFilter) return false
    if (typeFilter !== 'all' && item.media_type !== typeFilter) return false
    return true
  })

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Loading watch list...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">My Watch List</h1>
            <p className="text-slate-400">Keep track of movies and shows you want to watch</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
          >
            {showAddForm ? 'Cancel' : '+ Add Item'}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-900/50 border border-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Add Form */}
        {showAddForm && (
          <div className="mb-6 bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-xl font-bold mb-4">Add to Watch List</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Title *</label>
                <input
                  type="text"
                  value={addFormData.title}
                  onChange={(e) => setAddFormData({ ...addFormData, title: e.target.value })}
                  placeholder="Movie or Show Title"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Type</label>
                  <select
                    value={addFormData.media_type}
                    onChange={(e) => setAddFormData({ ...addFormData, media_type: e.target.value as 'movie' | 'series' })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="movie">Movie</option>
                    <option value="series">TV Series</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Priority</label>
                  <select
                    value={addFormData.priority}
                    onChange={(e) => setAddFormData({ ...addFormData, priority: e.target.value as 'low' | 'medium' | 'high' })}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">TMDB ID (Optional)</label>
                  <input
                    type="number"
                    value={addFormData.tmdb_id}
                    onChange={(e) => setAddFormData({ ...addFormData, tmdb_id: e.target.value })}
                    placeholder="12345"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Notes (Optional)</label>
                <textarea
                  value={addFormData.notes}
                  onChange={(e) => setAddFormData({ ...addFormData, notes: e.target.value })}
                  placeholder="Add any notes about this item..."
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleAddItem}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
              >
                Add to Watch List
              </button>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="unwatched">Unwatched</option>
                <option value="watched">Watched</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Priority</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as any)}
                className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Type</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as any)}
                className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value="movie">Movies</option>
                <option value="series">TV Series</option>
              </select>
            </div>
            <div className="flex items-end">
              <span className="text-sm text-slate-400">
                {filteredItems.length} of {watchList.length} items
              </span>
            </div>
          </div>
        </div>

        {/* Watch List Items */}
        {filteredItems.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-12 text-center border border-slate-700">
            <svg className="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <h3 className="text-xl font-bold mb-2">No Items Found</h3>
            <p className="text-slate-400">
              {filter === 'unwatched' ? 'All caught up! No unwatched items.' : 
               filter === 'watched' ? 'No watched items yet.' : 
               'Your watch list is empty. Add some items to get started!'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className={`bg-slate-800 rounded-lg border border-slate-700 overflow-hidden hover:border-blue-500 transition-colors ${
                  item.watched_at ? 'opacity-60' : ''
                }`}
              >
                <div className="p-4">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg mb-1">{item.title}</h3>
                      <div className="flex items-center gap-2 text-xs">
                        <span className={`px-2 py-0.5 rounded ${
                          item.media_type === 'movie' ? 'bg-purple-900/50 text-purple-300' : 'bg-blue-900/50 text-blue-300'
                        }`}>
                          {item.media_type === 'movie' ? 'Movie' : 'Series'}
                        </span>
                        <span className={`px-2 py-0.5 rounded ${
                          item.priority === 'high' ? 'bg-red-900/50 text-red-300' :
                          item.priority === 'medium' ? 'bg-yellow-900/50 text-yellow-300' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {item.priority.charAt(0).toUpperCase() + item.priority.slice(1)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Notes */}
                  {item.notes && (
                    <p className="text-sm text-slate-400 mb-3 line-clamp-2">{item.notes}</p>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
                    <span>Added {new Date(item.added_at).toLocaleDateString()}</span>
                    {item.watched_at && (
                      <span className="text-green-400">✓ Watched</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    {!item.watched_at && (
                      <button
                        onClick={() => handleMarkWatched(item.id)}
                        className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors"
                      >
                        Mark Watched
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-sm font-medium transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
