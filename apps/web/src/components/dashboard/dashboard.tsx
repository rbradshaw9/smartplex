'use client'

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User } from '@supabase/supabase-js'
import { ChatPanel } from './chat-panel'
import { WatchStats } from './watch-stats'
import { Recommendations } from './recommendations'
import { Database } from '@smartplex/db/types'

interface DashboardProps {
  user: User
  userStats: {
    totalWatched: number
    hoursWatched: number
    favoriteGenre: string
    recentlyWatched: Array<{
      title: string
      type: string
      watchedAt: string
    }>
  }
  recommendations: Array<{
    title: string
    reason: string
  }>
}

export function Dashboard({ user, userStats: initialStats, recommendations: initialRecommendations }: DashboardProps) {
  const [userStats, setUserStats] = useState(initialStats)
  const [recommendations, setRecommendations] = useState(initialRecommendations)
  const [fetchingData, setFetchingData] = useState(true)
  // Create Supabase client only once to avoid SSR mismatch
  const [supabase] = useState(() => createClientComponentClient<Database>())

  // Fetch real Plex data on mount
  useEffect(() => {
    const fetchPlexData = async () => {
      try {
        // Get Plex token from localStorage
        const plexToken = localStorage.getItem('plex_token')
        if (!plexToken) {
          console.error('No Plex token found')
          setFetchingData(false)
          return
        }

        // Fetch watch history and stats
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/plex/watch-history?plex_token=${plexToken}&limit=50`,
          {
            headers: {
              'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch Plex data')
        }

        const data = await response.json()

        console.log('Plex API response:', data)
        console.log('First watch_history item:', data.watch_history?.[0])

        // Calculate favorite genre from watch history
        const genreCounts: Record<string, number> = {}
        if (data.watch_history && Array.isArray(data.watch_history)) {
          data.watch_history.forEach((item: any) => {
            // Check multiple possible genre field names
            const genres = item.genres || item.genre || []
            const genreArray = Array.isArray(genres) ? genres : [genres].filter(Boolean)
            
            genreArray.forEach((genre: string) => {
              if (genre && typeof genre === 'string') {
                genreCounts[genre] = (genreCounts[genre] || 0) + 1
              }
            })
          })
        }
        
        const sortedGenres = Object.entries(genreCounts).sort((a, b) => b[1] - a[1])
        const favoriteGenre = sortedGenres.length > 0 ? sortedGenres[0][0] : 'No genre data yet'

        console.log('Genre counts:', genreCounts)
        console.log('Favorite genre:', favoriteGenre)

        // Update stats
        setUserStats({
          totalWatched: data.stats?.total_watched || 0,
          hoursWatched: data.stats?.total_hours || 0,
          favoriteGenre,
          recentlyWatched: (data.watch_history || []).slice(0, 10).map((item: any) => ({
            title: item.title || 'Unknown',
            type: item.type || 'unknown',
            watchedAt: item.last_viewed_at || new Date().toISOString(),
          })),
        })

        // Fetch AI recommendations
        try {
          const recsResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/ai/recommendations`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
              },
              body: JSON.stringify({
                user_id: user.id,
                limit: 5,
              }),
            }
          )
          
          if (recsResponse.ok) {
            const recsData = await recsResponse.json()
            if (recsData.recommendations && recsData.recommendations.length > 0) {
              setRecommendations(recsData.recommendations.map((rec: any) => ({
                title: rec.title,
                reason: rec.reason,
              })))
            }
          } else {
            console.error('Failed to fetch AI recommendations:', recsResponse.statusText)
          }
        } catch (error) {
          console.error('Error fetching AI recommendations:', error)
        }

        setFetchingData(false)
      } catch (error) {
        console.error('Failed to fetch Plex data:', error)
        setFetchingData(false)
      }
    }

    fetchPlexData()
  }, [supabase])

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {fetchingData && (
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-8">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400"></div>
              <p className="text-blue-400">Fetching your Plex watch history and ratings...</p>
            </div>
          </div>
        )}
        
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Stats & Recommendations */}
          <div className="lg:col-span-2 space-y-8">
            <WatchStats stats={userStats} />
            <Recommendations recommendations={recommendations} />
          </div>

          {/* Right Column - Chat Panel */}
          <div className="lg:col-span-1">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  )
}