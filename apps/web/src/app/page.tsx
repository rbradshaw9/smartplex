import { redirect } from 'next/navigation'
import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { LoginForm } from '@/components/auth/login-form'
import { Database } from '@smartplex/db/types'

export default async function Home() {
  const cookieStore = await cookies()
  const supabase = createServerComponentClient<Database>({
    cookies: () => cookieStore,
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
          <div className="text-center mb-12">
            <div className="mb-8">
              <div className="inline-block bg-blue-600/20 text-blue-300 px-4 py-2 rounded-full text-sm font-semibold mb-4">
                🚀 Now in Beta
              </div>
              <h1 className="text-6xl font-bold text-white mb-4">
                Smart<span className="text-blue-400">Plex</span>
              </h1>
              <p className="text-2xl text-slate-200 max-w-3xl mx-auto mb-4">
                Your personal AI companion for Plex
              </p>
              <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                Discover what to watch next with intelligent recommendations tailored to your taste. 
                Request new content instantly. All from one beautiful dashboard.
              </p>
            </div>
          </div>

          {/* Features for Users */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-xl border border-white/10 hover:border-blue-400/50 transition-colors">
              <div className="text-blue-400 text-4xl mb-4">�</div>
              <h3 className="text-white text-xl font-semibold mb-3">Personalized for You</h3>
              <p className="text-slate-300 text-sm">
                Get movie and TV show recommendations based on what you actually watch and love. 
                No more scrolling endlessly.
              </p>
            </div>

            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-xl border border-white/10 hover:border-blue-400/50 transition-colors">
              <div className="text-blue-400 text-4xl mb-4">✨</div>
              <h3 className="text-white text-xl font-semibold mb-3">One-Click Requests</h3>
              <p className="text-slate-300 text-sm">
                Found something you want to watch? Request it with a single click. 
                We'll handle the rest.
              </p>
            </div>

            <div className="bg-white/5 backdrop-blur-sm p-6 rounded-xl border border-white/10 hover:border-blue-400/50 transition-colors">
              <div className="text-blue-400 text-4xl mb-4">💬</div>
              <h3 className="text-white text-xl font-semibold mb-3">Chat with AI</h3>
              <p className="text-slate-300 text-sm">
                "What should I watch tonight?" Just ask. Our AI understands your mood 
                and suggests the perfect pick.
              </p>
            </div>
          </div>

          {/* Coming Soon for Admins */}
          <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-400/30 rounded-xl p-8 mb-12">
            <div className="flex items-start gap-4">
              <div className="text-purple-400 text-3xl">🔧</div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-white text-2xl font-semibold">For Server Admins</h3>
                  <span className="bg-purple-600/30 text-purple-200 px-3 py-1 rounded-full text-xs font-semibold">
                    Coming Soon
                  </span>
                </div>
                <p className="text-slate-300 mb-4">
                  Powerful tools for Plex server administrators are in development:
                </p>
                <div className="grid md:grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-purple-400">→</span> Intelligent library cleanup & storage management
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-purple-400">→</span> Automated deletion rules based on viewing patterns
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-purple-400">→</span> Real-time sync monitoring & analytics
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-purple-400">→</span> Integration with Sonarr, Radarr & Overseerr
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Login Section */}
          <div className="max-w-md mx-auto">
            <div className="bg-white/10 backdrop-blur-sm p-8 rounded-xl border border-white/20 shadow-2xl">
              <h2 className="text-2xl font-semibold text-white text-center mb-2">
                Get Started
              </h2>
              <p className="text-slate-400 text-center text-sm mb-6">
                Sign in with your Plex account to start your free beta
              </p>
              <LoginForm />
              <div className="mt-6 pt-6 border-t border-white/10">
                <p className="text-slate-400 text-xs text-center">
                  By signing in, you agree to our{' '}
                  <a href="/terms" className="text-blue-400 hover:text-blue-300 underline">Terms of Service</a>
                  {' '}and{' '}
                  <a href="/privacy" className="text-blue-400 hover:text-blue-300 underline">Privacy Policy</a>.
                  <br />
                  Your feedback helps us improve!
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}