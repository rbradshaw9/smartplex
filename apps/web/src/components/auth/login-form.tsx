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

  const handleOAuthLogin = async (provider: 'github' | 'google') => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase.auth.signInWithOAuth({
        provider,
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
      
      <div className="space-y-2">
        <button
          onClick={() => handleOAuthLogin('github')}
          disabled={loading}
          className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed 
                     text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center 
                     justify-center space-x-2 border border-slate-600"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Connecting...</span>
            </>
          ) : (
            <>
              <span>🐙</span>
              <span>Continue with GitHub</span>
            </>
          )}
        </button>

        <button
          onClick={() => handleOAuthLogin('google')}
          disabled={loading}
          className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed 
                     text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center 
                     justify-center space-x-2 border border-slate-600"
        >
          <span>�</span>
          <span>Continue with Google</span>
        </button>
      </div>

      <p className="text-xs text-slate-400 text-center">
        By continuing, you agree to SmartPlex&apos;s Terms of Service and Privacy Policy.
        <br />
        <span className="text-blue-400 font-medium">
          Plex authentication coming soon!
        </span>
      </p>
    </div>
  )
}