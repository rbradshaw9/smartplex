'use client'

import { useState } from 'react'

interface RecommendationsProps {
  recommendations: Array<{
    title: string
    reason: string
    type?: string
    year?: number
  }>
  onReload?: () => void
  isLoading?: boolean
}

export function Recommendations({ recommendations, onReload, isLoading = false }: RecommendationsProps) {
  console.log('🎬 Recommendations component rendering with:', recommendations)
  
  const [filter, setFilter] = useState<'all' | 'movie' | 'series'>('all')
  const [genreFilter, setGenreFilter] = useState<string>('all')
  
  // Filter recommendations based on selected filters
  const filteredRecommendations = recommendations.filter(item => {
    // Only filter if a specific type is selected AND the item has a type
    if (filter !== 'all' && item.type && item.type !== filter) return false
    // Genre filtering would require genre data from API
    return true
  })
  
  // Extract unique genres from recommendations (if available)
  const availableGenres = ['all', 'action', 'comedy', 'drama', 'sci-fi', 'thriller']
  
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
          filteredRecommendations.map((item, index) => (
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
                  <p className="text-slate-400 text-sm mt-2 line-clamp-2">{item.reason}</p>
                </div>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors flex-shrink-0">
                  Request
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-slate-700/50 rounded-lg p-8 text-center">
            <div className="text-4xl mb-3">🎬</div>
            <p className="text-slate-400">
              {isLoading ? 'Loading recommendations...' : 'No recommendations found. Try adjusting your filters!'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 p-4 bg-blue-600/10 border border-blue-600/20 rounded-lg">
        <div className="flex items-center space-x-2">
          <span className="text-blue-400 text-lg">🤖</span>
          <span className="text-blue-300 text-sm font-medium">
            AI Tip: These recommendations are based on your viewing history, ratings, and trending content. Use filters to narrow down what you're looking for!
          </span>
        </div>
      </div>
    </div>
  )
}