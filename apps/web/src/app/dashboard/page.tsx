'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { Dashboard } from '@/components/dashboard/dashboard'
import { Database } from '@smartplex/db/types'
import { User } from '@supabase/supabase-js'

interface Recommendation {
  title: string
  reason: string
}

// Force client-side only rendering to avoid SSR hydration issues
export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const router = useRouter()
  const [supabase] = useState(() => createClientComponentClient<Database>())

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session) {
        router.push('/')
        return
      }
      
      setUser(session.user)
      setLoading(false)
      
      // Fetch AI recommendations
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/ai/recommendations`,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            },
          }
        )
        
        if (response.ok) {
          const data = await response.json()
          console.log('📊 Fetched recommendations:', data)
          // API returns array directly, not wrapped in object
          if (Array.isArray(data)) {
            console.log('✅ Setting recommendations in page:', data)
            setRecommendations(data)
          } else if (data.recommendations && Array.isArray(data.recommendations)) {
            console.log('✅ Setting recommendations in page (wrapped):', data.recommendations)
            setRecommendations(data.recommendations)
          } else {
            console.log('⚠️ Unexpected recommendations format:', data)
          }
        }
      } catch (error) {
        console.error('Failed to fetch recommendations:', error)
      }
    }

    checkAuth()
  }, [router, supabase])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto mb-4"></div>
          <p className="text-slate-300">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const mockUserStats = {
    totalWatched: 0,
    hoursWatched: 0,
    favoriteGenre: 'Loading...',
    recentlyWatched: [],
  }

  return (
    <>
      <Dashboard 
        user={user} 
        userStats={mockUserStats}
        recommendations={recommendations}
      />
      {/* Hidden Sentry test button - press Shift+Ctrl+S to trigger */}
      <button
        onClick={() => {
          throw new Error("Sentry Test Error - Button Clicked");
        }}
        onKeyDown={(e) => {
          if (e.shiftKey && e.ctrlKey && e.key === 'S') {
            throw new Error("Sentry Test Error - Keyboard Shortcut");
          }
        }}
        style={{ 
          position: 'fixed', 
          bottom: '10px', 
          right: '10px', 
          opacity: 0.01,
          width: '50px',
          height: '50px',
          cursor: 'pointer'
        }}
        aria-label="Test Sentry"
      >
        Test
      </button>
    </>
  )
}