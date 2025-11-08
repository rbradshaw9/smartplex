'use client'

import { useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'
import { Database } from '@smartplex/db/types'

export function LoginForm() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClientComponentClient<Database>()

  const handlePlexLogin = async () => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github', // Temporary: Use GitHub OAuth as Plex OAuth proxy
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      })

      if (error) {
        setError(error.message)
      }
    } catch (err) {
      setError('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm">
          {error}
        </div>
      )}
      
      <button
        onClick={handlePlexLogin}
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed 
                   text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center 
                   justify-center space-x-2"
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            <span>Connecting...</span>
          </>
        ) : (
          <>
            <span className="text-lg">🎬</span>
            <span>Continue with Plex</span>
          </>
        )}
      </button>

      <p className="text-xs text-slate-400 text-center">
        By continuing, you agree to SmartPlex&apos;s Terms of Service and Privacy Policy.
        <br />
        <span className="text-yellow-400 font-medium">
          Note: Currently using GitHub OAuth as Plex OAuth proxy for demo
        </span>
      </p>
    </div>
  )
}