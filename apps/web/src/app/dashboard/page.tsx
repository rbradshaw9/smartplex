import { redirect } from 'next/navigation'
import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { Dashboard } from '@/components/dashboard/dashboard'
import { Database } from '@smartplex/db/types'

export default async function DashboardPage() {
  const supabase = createServerComponentClient<Database>({
    cookies,
  })

  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    redirect('/')
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
      user={session.user} 
      userStats={mockUserStats}
      recommendations={mockRecommendations}
    />
  )
}