'use client'

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter, usePathname } from 'next/navigation'
import { User } from '@supabase/supabase-js'
import { Database } from '@smartplex/db/types'

interface HeaderProps {
  user?: User | null
}

export function Header({ user }: HeaderProps) {
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  const supabase = createClientComponentClient<Database>()

  // Check if user is admin
  useEffect(() => {
    if (!user) return

    const checkAdminStatus = async () => {
      try {
        const { data } = await supabase
          .from('users')
          .select('role')
          .eq('id', user.id)
          .single()
        
        if (data?.role === 'admin') {
          setIsAdmin(true)
        }
      } catch (error) {
        console.error('Error checking admin status:', error)
      }
    }
    
    checkAdminStatus()
  }, [user, supabase])

  const handleSignOut = async () => {
    setLoading(true)
    await supabase.auth.signOut()
    router.push('/')
    setLoading(false)
  }

  const isActive = (path: string) => {
    return pathname === path
  }

  return (
    <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <button
              onClick={() => router.push('/dashboard')}
              className="text-2xl font-bold text-white hover:text-blue-400 transition-colors"
            >
              Smart<span className="text-blue-400">Plex</span>
            </button>
            
            {user && (
              <nav className="hidden md:flex items-center space-x-4">
                <button
                  onClick={() => router.push('/dashboard')}
                  className={`px-3 py-2 rounded-lg transition-colors ${
                    isActive('/dashboard')
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
                  }`}
                >
                  📊 Dashboard
                </button>

                {isAdmin && (
                  <>
                    <button
                      onClick={() => router.push('/admin/integrations')}
                      className={`px-3 py-2 rounded-lg transition-colors ${
                        isActive('/admin/integrations')
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-300 hover:text-white hover:bg-blue-600/50'
                      }`}
                    >
                      ⚙️ Integrations
                    </button>
                    <button
                      onClick={() => router.push('/admin/deletion')}
                      className={`px-3 py-2 rounded-lg transition-colors ${
                        isActive('/admin/deletion')
                          ? 'bg-purple-600 text-white'
                          : 'text-slate-300 hover:text-white hover:bg-purple-600/50'
                      }`}
                    >
                      🗑️ Cleanup
                    </button>
                  </>
                )}
              </nav>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <div className="hidden sm:block text-sm text-slate-300">
                  {user.email}
                  {isAdmin && (
                    <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                      Admin
                    </span>
                  )}
                </div>
                <button
                  onClick={handleSignOut}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors text-sm"
                >
                  {loading ? 'Signing out...' : 'Sign Out'}
                </button>
              </>
            ) : (
              <button
                onClick={() => router.push('/')}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
