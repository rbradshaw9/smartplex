'use client'

import { useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { Database } from '@smartplex/db/types'

interface RecommendationsProps {
  recommendations: Array<{
    title: string
    reason: string
    type?: string
    year?: number
    tmdb_id?: number
  }>
  onReload?: () => void
  isLoading?: boolean
}

export function Recommendations({ recommendations, onReload, isLoading = false }: RecommendationsProps) {
  console.log('🎬 Recommendations component rendering with:', recommendations)
  
  const [filter, setFilter] = useState<'all' | 'movie' | 'series'>('all')
  const [genreFilter, setGenreFilter] = useState<string>('all')
  const [requestingIndex, setRequestingIndex] = useState<number | null>(null)
  const [requestedIndices, setRequestedIndices] = useState<Set<number>>(new Set())
  const [visibleCount, setVisibleCount] = useState(5)
  const [overseerrAvailable, setOverseerrAvailable] = useState<boolean | null>(null)
  const [serverName, setServerName] = useState<string>('')
  const supabase = createClientComponentClient<Database>()
  
  // Check if Overseerr integration is available
  useState(() => {
    const checkOverseerr = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) return
        
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/integrations/overseerr/status`,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            },
          }
        )
        
        if (response.ok) {
          const data = await response.json()
          setOverseerrAvailable(data.available)
          if (data.server?.name) {
            setServerName(data.server.name)
          }
        }
      } catch (error) {
        console.error('Failed to check Overseerr status:', error)
        setOverseerrAvailable(false)
      }
    }
    checkOverseerr()
  })
  
  // Filter recommendations based on selected filters
  const filteredRecommendations = recommendations.filter(item => {
    // Only filter if a specific type is selected AND the item has a type
    if (filter !== 'all' && item.type && item.type !== filter) return false
    // Genre filtering would require genre data from API
    return true
  })
  
  // Extract unique genres from recommendations (if available)
  const availableGenres = ['all', 'action', 'comedy', 'drama', 'sci-fi', 'thriller']
  
  const handleRequest = async (item: typeof recommendations[0], index: number) => {
    setRequestingIndex(index)
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        alert('Please sign in to make requests')
        return
      }
      
      // Search for the media in Overseerr via our API
      const searchResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/integrations/overseerr/search?query=${encodeURIComponent(item.title)}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        }
      )
      
      if (!searchResponse.ok) {
        throw new Error('Search failed')
      }
      
      const searchResults = await searchResponse.json()
      
      // Find the best match (exact title + year match if available)
      let bestMatch = searchResults.results?.[0]
      if (item.year && searchResults.results) {
        const yearStr = item.year.toString()
        const yearMatch = searchResults.results.find((r: any) => 
          (r.name === item.title && r.first_air_date?.startsWith(yearStr)) ||
          (r.title === item.title && r.release_date?.startsWith(yearStr))
        )
        if (yearMatch) bestMatch = yearMatch
      }
      
      if (!bestMatch) {
        alert('❌ Could not find this title in TMDB. Try searching manually in Overseerr.')
        return
      }
      
      // Create request in Overseerr
      const mediaType = item.type === 'series' ? 'tv' : 'movie'
      const mediaId = bestMatch.id
      
      const requestResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/integrations/overseerr/request`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            media_type: mediaType,
            media_id: mediaId,
            is_4k: false,
          }),
        }
      )
      
      if (requestResponse.ok) {
        const result = await requestResponse.json()
        setRequestedIndices(prev => {
          const newSet = new Set(prev)
          newSet.add(index)
          return newSet
        })
        alert(`✅ Successfully requested: ${item.title}\n\nRequest ID: ${result.id}\nStatus: ${result.status}`)
      } else {
        const error = await requestResponse.json()
        if (error.detail?.includes('already exists')) {
          alert(`ℹ️ "${item.title}" has already been requested or is available!`)
        } else {
          throw new Error(error.detail || 'Request failed')
        }
      }
    } catch (error: any) {
      console.error('Request error:', error)
      alert(`❌ Failed to request "${item.title}": ${error.message}`)
    } finally {
      setRequestingIndex(null)
    }
  }
  
  const handleLoadMore = () => {
    setVisibleCount(prev => prev + 5)
  }
  
  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-white">AI Recommendations</h2>
        <button
          onClick={onReload}
          disabled={isLoading}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm transition-colors"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Loading...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </>
          )}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'all' 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('movie')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'movie' 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            🎬 Movies
          </button>
          <button
            onClick={() => setFilter('series')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'series' 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            📺 Series
          </button>
        </div>
        
        {/* Genre filter dropdown */}
        <select
          value={genreFilter}
          onChange={(e) => setGenreFilter(e.target.value)}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-700 text-slate-300 border border-slate-600 hover:bg-slate-600 transition-colors"
        >
          <option value="all">All Genres</option>
          {availableGenres.slice(1).map(genre => (
            <option key={genre} value={genre}>
              {genre.charAt(0).toUpperCase() + genre.slice(1)}
            </option>
          ))}
        </select>
      </div>
      
      <div className="space-y-4">
        {filteredRecommendations && filteredRecommendations.length > 0 ? (
          <>
            {filteredRecommendations.slice(0, visibleCount).map((item, index) => (
              <div key={index} className="bg-slate-700 rounded-lg p-4 hover:bg-slate-600/50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-white font-medium">{item.title}</h3>
                      {item.year && (
                        <span className="text-slate-500 text-sm">({item.year})</span>
                      )}
                      {item.type && (
                        <span className="text-xs px-2 py-1 rounded bg-slate-600 text-slate-300">
                          {item.type === 'movie' ? '🎬' : '📺'} {item.type}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-400 text-sm mt-2">{item.reason}</p>
                  </div>
                  {overseerrAvailable === true && (
                    <div className="flex flex-col items-end gap-1 flex-shrink-0">
                      <button 
                        onClick={() => handleRequest(item, index)}
                        disabled={requestingIndex === index || requestedIndices.has(index)}
                        className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                          requestedIndices.has(index)
                            ? 'bg-green-600 text-white cursor-default'
                            : requestingIndex === index
                            ? 'bg-blue-800 text-white cursor-wait'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        }`}
                        title={serverName ? `This will request to ${serverName}'s library` : 'Request media'}
                      >
                        {requestedIndices.has(index) ? (
                          <>✓ Requested</>
                        ) : requestingIndex === index ? (
                          <>
                            <svg className="animate-spin inline h-4 w-4" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                          </>
                        ) : (
                          'Request'
                        )}
                      </button>
                      {serverName && (
                        <span className="text-xs text-slate-500">→ {serverName}</span>
                      )}
                    </div>
                  )}
                  {overseerrAvailable === false && (
                    <div className="text-xs text-slate-500 text-right flex-shrink-0">
                      <p>Requests disabled</p>
                      <p>(No Overseerr)</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Load More Button */}
            {visibleCount < filteredRecommendations.length && (
              <div className="text-center pt-4">
                <button
                  onClick={handleLoadMore}
                  className="bg-slate-700 hover:bg-slate-600 text-slate-300 px-6 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Load More ({filteredRecommendations.length - visibleCount} remaining)
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="bg-slate-700/50 rounded-lg p-8 text-center">
            <div className="text-4xl mb-3">🎬</div>
            <p className="text-slate-400">
              {isLoading ? 'Loading recommendations...' : 'No recommendations found. Try adjusting your filters!'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 p-4 bg-gradient-to-r from-blue-600/10 to-purple-600/10 border border-blue-600/20 rounded-lg">
        <div className="flex items-start gap-3">
          <span className="text-blue-400 text-2xl">🤖</span>
          <div className="flex-1">
            <h4 className="text-blue-300 text-sm font-semibold mb-1">AI-Powered Recommendations</h4>
            <p className="text-slate-400 text-xs leading-relaxed">
              These suggestions are personalized based on your viewing history, ratings, and trending content. 
              Click "Request" to add titles to your Overseerr queue for automatic download.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}