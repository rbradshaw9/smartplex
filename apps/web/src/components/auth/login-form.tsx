'use client'

import { useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'
import { Database } from '@smartplex/db/types'

export function LoginForm() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const router = useRouter()
  const supabase = createClientComponentClient<Database>()

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)

      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          },
        })

        if (signUpError) throw signUpError
        router.push('/setup/connect-plex')
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        })

        if (signInError) throw signInError
        router.push('/dashboard')
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="text-center">
        <div className="text-6xl mb-4">🎬</div>
        <h2 className="text-2xl font-bold text-white mb-2">
          {isSignUp ? 'Create Your SmartPlex Account' : 'Welcome Back'}
        </h2>
        <p className="text-slate-400 text-sm">
          {isSignUp 
            ? "You'll connect your Plex server after creating your account" 
            : 'Sign in to manage your Plex ecosystem'}
        </p>
      </div>
      
      <form onSubmit={handleEmailAuth} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
            Email Address
          </label>
          <input
            type="email"
            id="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 
                       text-white placeholder-slate-400 focus:outline-none focus:ring-2 
                       focus:ring-orange-500 focus:border-transparent"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
            Password
          </label>
          <input
            type="password"
            id="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 
                       text-white placeholder-slate-400 focus:outline-none focus:ring-2 
                       focus:ring-orange-500 focus:border-transparent"
            placeholder={isSignUp ? "Create a strong password" : "Enter your password"}
            minLength={6}
          />
          {isSignUp && (
            <p className="text-xs text-slate-400 mt-1">
              Must be at least 6 characters
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 
                     disabled:cursor-not-allowed text-white font-medium py-3 px-4 
                     rounded-lg transition-colors flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Processing...</span>
            </>
          ) : (
            <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
          )}
        </button>
      </form>

      <div className="text-center">
        <button
          type="button"
          onClick={() => {
            setIsSignUp(!isSignUp)
            setError(null)
          }}
          className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
        >
          {isSignUp ? (
            <>
              Already have an account? <span className="text-orange-400 font-medium">Sign in</span>
            </>
          ) : (
            <>
              Don&apos;t have an account? <span className="text-orange-400 font-medium">Sign up</span>
            </>
          )}
        </button>
      </div>

      <div className="border-t border-slate-700 pt-4">
        <p className="text-xs text-slate-400 text-center">
          By continuing, you agree to SmartPlex&apos;s Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
