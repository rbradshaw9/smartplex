'use client'

import { useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'

interface AdminModeToggleProps {
  isAdmin: boolean
}

export function AdminModeToggle({ isAdmin }: AdminModeToggleProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  
  if (!isAdmin) return null
  
  const isAdminMode = pathname.startsWith('/admin')
  
  const handleModeSwitch = () => {
    if (isAdminMode) {
      // Switch to user mode
      router.push('/dashboard')
    } else {
      // Switch to admin mode
      router.push('/admin/integrations')
    }
    setShowDropdown(false)
  }
  
  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className={`px-4 py-2 rounded-lg font-medium transition-all ${
          isAdminMode 
            ? 'bg-purple-600 text-white hover:bg-purple-700' 
            : 'bg-slate-700 text-white hover:bg-slate-600'
        }`}
      >
        {isAdminMode ? '⚙️ Admin Mode' : '👤 User Mode'}
        <span className="ml-2 text-xs">▼</span>
      </button>
      
      {showDropdown && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setShowDropdown(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute right-0 mt-2 w-56 bg-slate-800 rounded-lg shadow-xl border border-slate-700 z-20">
            <div className="p-2">
              <button
                onClick={handleModeSwitch}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-slate-700 transition-colors"
              >
                {isAdminMode ? (
                  <>
                    <div className="flex items-center">
                      <span className="text-2xl mr-3">👤</span>
                      <div>
                        <div className="text-white font-medium">Switch to User Mode</div>
                        <div className="text-slate-400 text-xs">Personal dashboard & recommendations</div>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center">
                      <span className="text-2xl mr-3">⚙️</span>
                      <div>
                        <div className="text-white font-medium">Switch to Admin Mode</div>
                        <div className="text-slate-400 text-xs">Server management & cleanup</div>
                      </div>
                    </div>
                  </>
                )}
              </button>
            </div>
            
            <div className="border-t border-slate-700 p-2">
              <div className="px-4 py-2 text-slate-400 text-xs">
                {isAdminMode ? (
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-purple-500 rounded-full mr-2 animate-pulse"></span>
                    Admin features active
                  </span>
                ) : (
                  <span className="flex items-center">
                    <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                    Regular user view
                  </span>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
