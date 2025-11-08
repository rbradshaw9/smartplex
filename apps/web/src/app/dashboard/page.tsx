'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Dashboard } from '@/components/dashboard/dashboard'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for user session in localStorage (Plex auth)
    const userDataStr = localStorage.getItem('smartplex_user')
    const sessionDataStr = localStorage.getItem('smartplex_session')
    
    if (!userDataStr || !sessionDataStr) {
      router.push('/')
      return
    }

    try {
      const userData = JSON.parse(userDataStr)
      const sessionData = JSON.parse(sessionDataStr)
      
      // Check if session is expired
      const expiresAt = new Date(sessionData.expires_at)
      if (expiresAt < new Date()) {
        // Session expired, clear and redirect
        localStorage.removeItem('smartplex_user')
        localStorage.removeItem('smartplex_session')
        localStorage.removeItem('plex_token')
        router.push('/')
        return
      }

      setUser(userData)
      setLoading(false)
    } catch (error) {
      console.error('Failed to parse user data:', error)
      router.push('/')
    }
  }, [router])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  // Mock user data for demo
  const mockUserStats = {
    totalWatched: 156,
    hoursWatched: 248,
    favoriteGenre: 'Action',
    recentlyWatched: [
      { title: 'The Batman', type: 'movie', watchedAt: '2024-01-15' },
      { title: 'House of the Dragon S1E1', type: 'episode', watchedAt: '2024-01-14' },
      { title: 'Dune: Part One', type: 'movie', watchedAt: '2024-01-13' },
    ],
  }

  const mockRecommendations = [
    { title: 'Oppenheimer', reason: 'Popular drama like your recent watches' },
    { title: 'The Last of Us', reason: 'Trending series matching your preferences' },
    { title: 'Top Gun: Maverick', reason: 'Action movie based on your favorite genre' },
  ]

  return (
    <Dashboard 
      user={user} 
      userStats={mockUserStats}
      recommendations={mockRecommendations}
    />
  )
}