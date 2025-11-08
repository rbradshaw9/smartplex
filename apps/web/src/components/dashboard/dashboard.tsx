'use client'

import { useState } from 'react'
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

export function Dashboard({ user, userStats, recommendations }: DashboardProps) {
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const supabase = createClientComponentClient<Database>()

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