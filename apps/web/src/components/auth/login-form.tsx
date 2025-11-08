'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

export function LoginForm() {
  const router = useRouter()
  const supabase = createClient()
  
  const [showEmailLogin, setShowEmailLogin] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [plexPin, setPlexPin] = useState<{id: number, code: string} | null>(null)

  // Plex PIN-based OAuth flow (like Overseerr)
  const handlePlexLogin = async () => {
    setError('')
    setLoading(true)

    try {
      // Step 1: Get a PIN from Plex
      const pinResponse = await fetch('https://plex.tv/api/v2/pins', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-Plex-Product': 'SmartPlex',
          'X-Plex-Client-Identifier': crypto.randomUUID(),
        },
        body: JSON.stringify({
          strong: true,
        }),
      })

      if (!pinResponse.ok) throw new Error('Failed to generate Plex PIN')
      
      const pinData = await pinResponse.json()
      setPlexPin({ id: pinData.id, code: pinData.code })

      // Step 2: Open Plex auth in new window
      const authUrl = `https://app.plex.tv/auth#?clientID=${crypto.randomUUID()}&code=${pinData.code}&context%5Bdevice%5D%5Bproduct%5D=SmartPlex`
      window.open(authUrl, 'PlexAuth', 'width=600,height=700')

      // Step 3: Poll for auth token
      const pollInterval = setInterval(async () => {
        const checkResponse = await fetch(`https://plex.tv/api/v2/pins/${pinData.id}`, {
          headers: {
            'Accept': 'application/json',
            'X-Plex-Client-Identifier': crypto.randomUUID(),
          },
        })

        const checkData = await checkResponse.json()
        
        if (checkData.authToken) {
          clearInterval(pollInterval)
          
          // Step 4: Send token to our backend to create/login user
          const loginResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/plex/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              authToken: checkData.authToken 
            }),
          })

          if (!loginResponse.ok) throw new Error('Failed to authenticate with backend')
          
          const { user, session } = await loginResponse.json()
          
          // Step 5: Create Supabase session
          const { error: supabaseError } = await supabase.auth.signInWithPassword({
            email: user.email,
            password: checkData.authToken, // Use Plex token as password
          })

          if (supabaseError) {
            // If user doesn't exist in Supabase yet, create them
            const { error: signUpError } = await supabase.auth.signUp({
              email: user.email,
              password: checkData.authToken,
              options: {
                data: {
                  plex_username: user.plex_username,
                  plex_user_id: user.plex_user_id,
                  avatar_url: user.avatar_url,
                }
              }
            })
            if (signUpError) throw signUpError
          }

          setLoading(false)
          router.push('/dashboard')
        }
      }, 2000) // Poll every 2 seconds

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setError('Plex authentication timed out. Please try again.')
        setLoading(false)
        setPlexPin(null)
      }, 300000)

    } catch (err: any) {
      setError(err.message || 'Plex login failed')
      setLoading(false)
    }
  }

  // Email/Password authentication (secondary option)
  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        })
        if (error) throw error
        
        // After signup, user needs to connect Plex
        router.push('/setup/connect-plex')
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error

        // Check if user has Plex connected
        const { data: user } = await supabase.auth.getUser()
        const hasPlex = user?.user?.user_metadata?.plex_username

        if (!hasPlex) {
          router.push('/setup/connect-plex')
        } else {
          router.push('/dashboard')
        }
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-white">Welcome to SmartPlex</h2>
        <p className="mt-2 text-gray-400">Sign in to manage your Plex server</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Primary: Plex Login */}
      {!showEmailLogin ? (
        <div className="space-y-4">
          <button
            onClick={handlePlexLogin}
            disabled={loading}
            className="w-full bg-[#e5a00d] hover:bg-[#cc8f0c] text-black font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              plexPin ? (
                <>
                  <div className="animate-spin h-5 w-5 border-2 border-black border-t-transparent rounded-full" />
                  Waiting for Plex authorization... (PIN: {plexPin.code})
                </>
              ) : (
                <>
                  <div className="animate-spin h-5 w-5 border-2 border-black border-t-transparent rounded-full" />
                  Generating PIN...
                </>
              )
            ) : (
              <>
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
                </svg>
                Sign in with Plex
              </>
            )}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-900 text-gray-400">Or</span>
            </div>
          </div>

          <button
            onClick={() => setShowEmailLogin(true)}
            className="w-full bg-gray-800 hover:bg-gray-700 text-white py-3 px-4 rounded-lg transition-colors"
          >
            Sign in with Email
          </button>
        </div>
      ) : (
        /* Secondary: Email/Password */
        <form onSubmit={handleEmailAuth} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-[#e5a00d] focus:border-transparent outline-none"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-[#e5a00d] focus:border-transparent outline-none"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#e5a00d] hover:bg-[#cc8f0c] text-black font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-sm text-[#e5a00d] hover:text-[#cc8f0c]"
            >
              {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setShowEmailLogin(false)}
              className="text-sm text-gray-400 hover:text-gray-300"
            >
              ← Back to Plex login
            </button>
          </div>
        </form>
      )}

      <p className="text-xs text-center text-gray-500">
        {showEmailLogin 
          ? "You'll need to connect your Plex account after signing up"
          : "Sign in with your Plex account for the best experience"
        }
      </p>
    </div>
  )
}
