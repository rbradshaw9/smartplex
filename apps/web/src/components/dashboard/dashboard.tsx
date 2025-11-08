'use client'

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'
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
  const [loading, setLoading] = useState(false)
  const [userStats, setUserStats] = useState(initialStats)
  const [recommendations, setRecommendations] = useState(initialRecommendations)
  const [fetchingData, setFetchingData] = useState(true)
  const router = useRouter()
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

        // Calculate favorite genre from watch history
        const genreCounts: Record<string, number> = {}
        data.watch_history.forEach((item: any) => {
          item.genres?.forEach((genre: string) => {
            genreCounts[genre] = (genreCounts[genre] || 0) + 1
          })
        })
        const favoriteGenre = Object.entries(genreCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'Unknown'

        // Update stats
        setUserStats({
          totalWatched: data.stats.total_watched,
          hoursWatched: data.stats.total_hours,
          favoriteGenre,
          recentlyWatched: data.watch_history.slice(0, 10).map((item: any) => ({
            title: item.title,
            type: item.type,
            watchedAt: item.last_viewed_at,
          })),
        })

        // Fetch AI recommendations
        try {
          const recsResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/ai/recommendations`,
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

  const handleSignOut = async () => {
    setLoading(true)
    await supabase.auth.signOut()
    router.push('/')
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-white">
                Smart<span className="text-blue-400">Plex</span>
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-slate-300">
                Welcome, {user.email}
              </div>
              <button
                onClick={handleSignOut}
                disabled={loading}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
              >
                {loading ? 'Signing out...' : 'Sign Out'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
      </main>
    </div>
  )
}