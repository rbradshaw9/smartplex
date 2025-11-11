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
      // Generate consistent client identifier for this session
      const clientId = process.env.NEXT_PUBLIC_PLEX_CLIENT_ID || 'smartplex-web-client'
      
      // Step 1: Get a PIN from Plex
      const pinResponse = await fetch('https://plex.tv/api/v2/pins', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-Plex-Product': 'SmartPlex',
          'X-Plex-Client-Identifier': clientId,
        },
        body: JSON.stringify({
          strong: true,
        }),
      })

      if (!pinResponse.ok) throw new Error('Failed to generate Plex PIN')
      
      const pinData = await pinResponse.json()
      setPlexPin({ id: pinData.id, code: pinData.code })

      // Step 2: Open Plex auth in new window
      const authUrl = `https://app.plex.tv/auth#?clientID=${clientId}&code=${pinData.code}&context%5Bdevice%5D%5Bproduct%5D=SmartPlex`
      const authWindow = window.open(authUrl, 'PlexAuth', 'width=600,height=700')

      // Step 3: Poll for auth token
      let pollCount = 0
      const MAX_POLLS = 150 // 5 minutes at 2-second intervals
      
      const pollInterval = setInterval(async () => {
        pollCount++
        
        // Stop polling after max attempts
        if (pollCount > MAX_POLLS) {
          clearInterval(pollInterval)
          setError('Plex authentication timed out. Please try again.')
          setLoading(false)
          setPlexPin(null)
          return
        }
        
        try {
          const checkResponse = await fetch(`https://plex.tv/api/v2/pins/${pinData.id}`, {
            headers: {
              'Accept': 'application/json',
              'X-Plex-Client-Identifier': clientId,
            },
            signal: AbortSignal.timeout(5000), // 5 second timeout per request
          })

          if (!checkResponse.ok) {
            console.warn(`Poll failed with status: ${checkResponse.status}`)
            return // Continue polling on transient errors
          }

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
              signal: AbortSignal.timeout(30000), // 30 second timeout for login
            })

            if (!loginResponse.ok) {
              const errorData = await loginResponse.json().catch(() => ({}))
              throw new Error(errorData.detail || 'Failed to authenticate with backend')
            }
            
            const { user, supabase_session } = await loginResponse.json()
            
            console.log('Backend response:', { user, supabase_session })
            
            // Sign in to Supabase using the temporary password
            // This creates proper session cookies that the dashboard can use
            if (!supabase_session.temp_password) {
              throw new Error('No temporary password received from backend')
            }
            
            console.log('Signing in to Supabase with email:', supabase_session.email)
            
            const { error: signInError } = await supabase.auth.signInWithPassword({
              email: supabase_session.email,
              password: supabase_session.temp_password,
            })

            if (signInError) {
              console.error('Supabase sign-in error:', signInError)
              throw new Error(`Failed to establish Supabase session: ${signInError.message}`)
            }
            
            console.log('Successfully signed in to Supabase')
            
            // Store Plex token for API requests
            if (typeof window !== 'undefined') {
              localStorage.setItem('plex_token', checkData.authToken)
            }

            // Close the OAuth popup window
            if (authWindow && !authWindow.closed) {
              authWindow.close()
            }

            setLoading(false)
            router.push('/dashboard')
            router.refresh()
          }
        } catch (pollError: any) {
          console.error('Poll error:', pollError)
          // Continue polling on errors unless it's a fatal backend error
          if (pollError.message?.includes('Failed to authenticate with backend')) {
            clearInterval(pollInterval)
            setError(pollError.message)
            setLoading(false)
            setPlexPin(null)
          }
          // Otherwise continue polling - might be transient
        }
      }, 2000) // Poll every 2 seconds

      // Cleanup on unmount
      return () => {
        if (pollInterval) {
          clearInterval(pollInterval)
        }
      }

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
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          }
        })
        if (error) throw error
        
        // Show success message
        setError('')
        alert('Check your email for the confirmation link!')
      } else {
        const { error, data } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error

        // Store session info for authenticated requests (similar to Plex login)
        if (data.user && typeof window !== 'undefined') {
          localStorage.setItem('smartplex_user', JSON.stringify({
            id: data.user.id,
            email: data.user.email,
            display_name: data.user.user_metadata?.display_name,
          }))
        }

        // Redirect to dashboard
        router.push('/dashboard')
        router.refresh()
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
                  Waiting for Plex authorization...
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
