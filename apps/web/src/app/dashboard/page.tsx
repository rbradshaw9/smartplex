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

  // Plex token is stored in localStorage on the client
  // The dashboard component will fetch real data using useEffect
  // Server component just passes initial empty/loading state
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
      user={session.user} 
      userStats={mockUserStats}
      recommendations={mockRecommendations}
    />
  )
}