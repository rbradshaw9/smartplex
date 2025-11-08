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

  // Fetch user's Plex token from localStorage (client-side)
  // Note: This should be fetched from the database in production
  // For now, we'll pass mock data and let the client fetch real data
  
  // Fetch user profile to get Plex token
  let plexToken = null
  try {
    const { data: userData } = await supabase
      .table('users')
      .select('*')
      .eq('id', session.user.id)
      .single()
    
    // Note: plex_token is stored in localStorage on client, not in DB
    // We'll need to fetch it client-side
  } catch (error) {
    console.error('Failed to fetch user data:', error)
  }

  // Use mock data for now - the dashboard component will fetch real data client-side
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