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

  // Fetch real Plex data on mount with caching
  useEffect(() => {
    const fetchPlexData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        if (!apiUrl) {
          console.error('NEXT_PUBLIC_API_URL is not set')
          setFetchingData(false)
          return
        }

        console.log('API URL configured as:', apiUrl)
        if (!apiUrl.startsWith('https://')) {
          console.error('⚠️ WARNING: API_URL is HTTP not HTTPS! This will be blocked by browser.')
          console.error('⚠️ Go to Vercel → Settings → Environment Variables and change to HTTPS')
        }

        // First, try to load cached data from Supabase
        const { data: cachedStats, error: statsError } = await supabase
          .from('user_stats_cache')
          .select('*')
          .eq('user_id', user.id)
          .maybeSingle()

        const { data: cachedHistory } = await supabase
          .from('watch_history_cache')
          .select('*')
          .eq('user_id', user.id)
          .order('last_viewed_at', { ascending: false })
          .limit(10)

        const { data: cachedRecs, error: recsError } = await supabase
          .from('recommendations_cache')
          .select('*')
          .eq('user_id', user.id)
          .maybeSingle()

        // If we have recent cache (< 1 hour old), use it immediately
        const cacheAge = cachedStats?.last_updated_at 
          ? Date.now() - new Date(cachedStats.last_updated_at).getTime()
          : Infinity
        const isCacheFresh = cacheAge < 60 * 60 * 1000 // 1 hour

        if (isCacheFresh && cachedStats) {
          console.log('Using cached data (age:', Math.round(cacheAge / 1000 / 60), 'minutes)')
          
          setUserStats({
            totalWatched: cachedStats.total_watched || 0,
            hoursWatched: cachedStats.total_hours || 0,
            favoriteGenre: cachedStats.favorite_genre || 'No genre data yet',
            recentlyWatched: (cachedHistory || []).map((item: any) => ({
              title: item.title,
              type: item.type,
              watchedAt: item.last_viewed_at,
            })),
          })

          if (cachedRecs?.recommendations) {
            setRecommendations(cachedRecs.recommendations as any[])
          }

          setFetchingData(false)
          
          // Still fetch in background if cache is older than 5 minutes
          if (cacheAge > 5 * 60 * 1000) {
            fetchAndCacheData(apiUrl, true)
          }
          return
        }

        // No cache or stale cache - fetch fresh data
        console.log('No fresh cache, fetching from Plex API')
        await fetchAndCacheData(apiUrl, false)

      } catch (error) {
        console.error('Failed to load dashboard data:', error)
        setFetchingData(false)
      }
    }

    const fetchAndCacheData = async (apiUrl: string, isBackground: boolean) => {
      try {
        // Get Plex token from localStorage
        const plexToken = localStorage.getItem('plex_token')
        if (!plexToken) {
          console.error('No Plex token found')
          return
        }

        if (!isBackground) {
          console.log('Fetching Plex data from:', apiUrl)
        }

        // Fetch watch history and stats (reduce from 50 to 25 for speed)
        const response = await fetch(
          `${apiUrl}/api/plex/watch-history?plex_token=${plexToken}&limit=25`,
          {
            headers: {
              'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
            },
          }
        )

        if (!isBackground) {
          console.log('Plex watch history response:', response.status, response.statusText)
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch Plex data: ${response.status} ${response.statusText}`)
        }

        const data = await response.json()

        if (!isBackground) {
          console.log('Plex API response:', data)
        }

        // Calculate favorite genre from watch history
        const genreCounts: Record<string, number> = {}
        if (data.watch_history && Array.isArray(data.watch_history)) {
          data.watch_history.forEach((item: any) => {
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

        const statsData = {
          totalWatched: data.stats?.total_watched || 0,
          hoursWatched: data.stats?.total_hours || 0,
          favoriteGenre,
          recentlyWatched: (data.watch_history || []).slice(0, 10).map((item: any) => ({
            title: item.title || 'Unknown',
            type: item.type || 'unknown',
            watchedAt: item.last_viewed_at || new Date().toISOString(),
          })),
        }

        // Update UI if not background
        if (!isBackground) {
          setUserStats(statsData)
        }

        // Cache stats in Supabase
        await supabase
          .from('user_stats_cache')
          .upsert({
            user_id: user.id,
            total_watched: statsData.totalWatched,
            total_hours: statsData.hoursWatched,
            favorite_genre: statsData.favoriteGenre,
            stats_data: data.stats || {},
            last_updated_at: new Date().toISOString(),
          }, { onConflict: 'user_id' })

        // Cache watch history
        if (data.watch_history && data.watch_history.length > 0) {
          const historyRecords = data.watch_history.slice(0, 25).map((item: any) => ({
            user_id: user.id,
            plex_id: item.id || item.plex_id || `${item.title}-${item.year}`,
            title: item.title,
            type: item.type,
            year: item.year,
            duration: item.duration,
            last_viewed_at: item.last_viewed_at,
            view_count: item.view_count || 0,
            rating: item.rating,
            genres: item.genres || [],
            last_synced_at: new Date().toISOString(),
          }))

          await supabase
            .from('watch_history_cache')
            .upsert(historyRecords, { onConflict: 'user_id,plex_id' })
        }

        // Fetch AI recommendations (skip in background to avoid 502 errors)
        if (!isBackground) {
          try {
            const recsResponse = await fetch(
              `${apiUrl}/ai/recommendations`,
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
                const recs = recsData.recommendations.map((rec: any) => ({
                  title: rec.title,
                  reason: rec.reason,
                }))
                setRecommendations(recs)

                // Cache recommendations
                await supabase
                  .from('recommendations_cache')
                  .upsert({
                    user_id: user.id,
                    recommendations: recs,
                    last_updated_at: new Date().toISOString(),
                  }, { onConflict: 'user_id' })
              }
            }
          } catch (error) {
            console.error('Error fetching AI recommendations:', error)
          }
        }

        if (!isBackground) {
          setFetchingData(false)
        }
      } catch (error) {
        console.error('Failed to fetch and cache Plex data:', error)
        if (!isBackground) {
          setFetchingData(false)
        }
      }
    }

    fetchPlexData()
  }, [user.id, supabase])

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