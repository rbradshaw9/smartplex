import { redirect } from 'next/navigation'
import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { LoginForm } from '@/components/auth/login-form'
import { Database } from '@smartplex/db/types'

export default async function Home() {
  const supabase = createServerComponentClient<Database>({
    cookies,
  })

  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (session) {
    redirect('/dashboard')
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-6xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <div className="mb-8">
              <h1 className="text-6xl font-bold text-white mb-4">
                Smart<span className="text-blue-400">Plex</span>
              </h1>
              <p className="text-xl text-slate-300 max-w-2xl mx-auto">
                The autonomous, AI-powered Plex server ecosystem that intelligently 
                manages your media and delivers personalized recommendations.
              </p>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-lg border border-white/10">
              <div className="text-blue-400 text-4xl mb-4">🎬</div>
              <h3 className="text-white text-xl font-semibold mb-2">Smart Recommendations</h3>
              <p className="text-slate-300">
                AI-powered suggestions based on your watching habits and preferences.
              </p>
            </div>

            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-lg border border-white/10">
              <div className="text-blue-400 text-4xl mb-4">⚙️</div>
              <h3 className="text-white text-xl font-semibold mb-2">Automated Management</h3>
              <p className="text-slate-300">
                Intelligent cleanup and storage optimization for your Plex servers.
              </p>
            </div>

            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-lg border border-white/10">
              <div className="text-blue-400 text-4xl mb-4">🤖</div>
              <h3 className="text-white text-xl font-semibold mb-2">AI Chat Assistant</h3>
              <p className="text-slate-300">
                Conversational AI for discovering content and managing your library.
              </p>
            </div>
          </div>

          {/* Login Section */}
          <div className="max-w-md mx-auto">
            <div className="bg-white/10 backdrop-blur-sm p-8 rounded-lg border border-white/20">
              <h2 className="text-2xl font-semibold text-white text-center mb-6">
                Sign in with Plex
              </h2>
              <LoginForm />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}