'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { Dashboard } from '@/components/dashboard/dashboard'
import { Database } from '@smartplex/db/types'
import { User } from '@supabase/supabase-js'

// Force client-side only rendering to avoid SSR hydration issues
export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
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

  const mockRecommendations = [
    { title: 'Loading...', reason: 'Fetching your personalized recommendations' },
  ]

  return (
    <Dashboard 
      user={user} 
      userStats={mockUserStats}
      recommendations={mockRecommendations}
    />
  )
}