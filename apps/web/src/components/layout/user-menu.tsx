'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User } from '@supabase/supabase-js'
import { Database } from '@smartplex/db/types'

interface UserMenuProps {
  user: User
  isAdmin: boolean
}

export function UserMenu({ user, isAdmin }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const pathname = usePathname()
  const supabase = createClientComponentClient<Database>()

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleSignOut = async () => {
    setLoading(true)
    await supabase.auth.signOut()
    router.push('/')
    setLoading(false)
  }

  const handleNavigation = (path: string) => {
    setIsOpen(false)
    router.push(path)
  }

  // Get user initials for avatar
  const getInitials = () => {
    const email = user.email || ''
    return email.substring(0, 2).toUpperCase()
  }

  const isAdminPath = pathname.startsWith('/admin')

  return (
    <div className="relative" ref={menuRef}>
      {/* User Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-all ${
          isOpen 
            ? 'bg-slate-700 ring-2 ring-blue-500' 
            : 'hover:bg-slate-700/50'
        }`}
      >
        {/* Avatar Circle */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
          isAdmin 
            ? 'bg-gradient-to-br from-purple-500 to-blue-500 text-white' 
            : 'bg-gradient-to-br from-blue-500 to-cyan-500 text-white'
        }`}>
          {getInitials()}
        </div>

        {/* Email and Badge */}
        <div className="hidden md:block text-left">
          <div className="text-sm text-white truncate max-w-[150px]">
            {user.email}
          </div>
          {isAdmin && (
            <div className="text-xs text-purple-400 font-medium">
              Admin
            </div>
          )}
        </div>

        {/* Dropdown Arrow */}
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-2 z-50">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-slate-700">
            <div className="text-sm text-white font-medium truncate">
              {user.email}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {isAdmin ? 'Administrator Account' : 'User Account'}
            </div>
          </div>

          {/* Admin Section (only for admins) */}
          {isAdmin && (
            <>
              <div className="px-2 py-2 space-y-1">
                {isAdminPath ? (
                  // Show "Return to Dashboard" when in admin mode
                  <button
                    onClick={() => handleNavigation('/dashboard')}
                    className="w-full flex items-center px-3 py-2.5 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                  >
                    <span className="text-xl mr-3">👤</span>
                    <div className="text-left flex-1">
                      <div className="text-sm font-medium">Return to Dashboard</div>
                      <div className="text-xs opacity-75">
                        Exit admin mode
                      </div>
                    </div>
                  </button>
                ) : (
                  // Show "Administration" when in user mode
                  <button
                    onClick={() => handleNavigation('/admin/integrations')}
                    className="w-full flex items-center px-3 py-2.5 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                  >
                    <span className="text-xl mr-3">⚙️</span>
                    <div className="text-left flex-1">
                      <div className="text-sm font-medium">Administration</div>
                      <div className="text-xs opacity-75">
                        Server management & settings
                      </div>
                    </div>
                  </button>
                )}
              </div>
              <div className="border-t border-slate-700 my-2"></div>
            </>
          )}

          {/* User Options */}
          <div className="px-2 py-2 space-y-1">
            <button
              onClick={() => handleNavigation('/profile')}
              className="w-full flex items-center px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <span className="text-lg mr-3">👤</span>
              <span className="text-sm">Profile Settings</span>
            </button>

            <button
              onClick={() => handleNavigation('/profile/security')}
              className="w-full flex items-center px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <span className="text-lg mr-3">🔑</span>
              <span className="text-sm">Change Password</span>
            </button>

            <button
              onClick={() => handleNavigation('/profile/preferences')}
              className="w-full flex items-center px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <span className="text-lg mr-3">🎨</span>
              <span className="text-sm">Preferences</span>
            </button>
          </div>

          {/* Sign Out */}
          <div className="border-t border-slate-700 mt-2 px-2 py-2">
            <button
              onClick={handleSignOut}
              disabled={loading}
              className="w-full flex items-center px-3 py-2 rounded-lg text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors disabled:opacity-50"
            >
              <span className="text-lg mr-3">🚪</span>
              <span className="text-sm font-medium">
                {loading ? 'Signing out...' : 'Sign Out'}
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
