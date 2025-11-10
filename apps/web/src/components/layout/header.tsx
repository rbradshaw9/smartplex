'use client'

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter, usePathname } from 'next/navigation'
import { User } from '@supabase/supabase-js'
import { Database } from '@smartplex/db/types'
import { AdminModeToggle } from './admin-mode-toggle'

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
  
  const isAdminMode = pathname.startsWith('/admin')

  return (
    <header className={`border-b sticky top-0 z-50 ${
      isAdminMode 
        ? 'bg-gradient-to-r from-purple-900 to-slate-900 border-purple-700' 
        : 'bg-slate-800 border-slate-700'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <button
              onClick={() => router.push(isAdminMode ? '/admin/integrations' : '/dashboard')}
              className="text-2xl font-bold text-white hover:text-blue-400 transition-colors"
            >
              Smart<span className="text-blue-400">Plex</span>
              {isAdminMode && <span className="ml-2 text-sm text-purple-300">Admin</span>}
            </button>
            
            {user && (
              <nav className="hidden md:flex items-center space-x-4">
                {!isAdminMode ? (
                  // USER MODE NAVIGATION
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
                ) : (
                  // ADMIN MODE NAVIGATION
                  <>
                    <button
                      onClick={() => router.push('/admin/integrations')}
                      className={`px-3 py-2 rounded-lg transition-colors ${
                        isActive('/admin/integrations')
                          ? 'bg-purple-600 text-white'
                          : 'text-purple-200 hover:text-white hover:bg-purple-600/50'
                      }`}
                    >
                      ⚙️ Integrations
                    </button>
                    <button
                      onClick={() => router.push('/admin/deletion')}
                      className={`px-3 py-2 rounded-lg transition-colors ${
                        isActive('/admin/deletion')
                          ? 'bg-purple-600 text-white'
                          : 'text-purple-200 hover:text-white hover:bg-purple-600/50'
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
                <AdminModeToggle isAdmin={isAdmin} />
                <div className="hidden sm:block text-sm text-slate-300">
                  {user.email}
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
