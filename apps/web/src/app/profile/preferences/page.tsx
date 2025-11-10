'use client'

import { useEffect, useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'

export default function PreferencesPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [theme, setTheme] = useState('dark')
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [recommendationsEnabled, setRecommendationsEnabled] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const supabase = createClientComponentClient()

  useEffect(() => {
    const loadPreferences = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/')
        return
      }

      // Load preferences from user metadata or database
      const { data: userData } = await supabase
        .from('users')
        .select('metadata')
        .eq('id', user.id)
        .single()

      if (userData?.metadata) {
        setTheme(userData.metadata.theme || 'dark')
        setEmailNotifications(userData.metadata.email_notifications !== false)
        setRecommendationsEnabled(userData.metadata.recommendations_enabled !== false)
      }

      setLoading(false)
    }
    
    loadPreferences()
  }, [supabase, router])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('Not authenticated')

      const preferences = {
        theme,
        email_notifications: emailNotifications,
        recommendations_enabled: recommendationsEnabled,
      }

      const { error } = await supabase
        .from('users')
        .update({ 
          metadata: preferences
        })
        .eq('id', user.id)

      if (error) throw error

      setMessage({ type: 'success', text: 'Preferences saved successfully!' })
    } catch (error) {
      console.error('Error saving preferences:', error)
      setMessage({ type: 'error', text: 'Failed to save preferences. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Preferences</h1>
          <p className="text-slate-400 mt-2">Customize your SmartPlex experience</p>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          {/* Appearance */}
          <div className="bg-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Appearance</h2>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Theme
              </label>
              <div className="space-y-2">
                <label className="flex items-center p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700 transition-colors">
                  <input
                    type="radio"
                    name="theme"
                    value="dark"
                    checked={theme === 'dark'}
                    onChange={(e) => setTheme(e.target.value)}
                    className="mr-3"
                  />
                  <div>
                    <div className="text-white font-medium">Dark</div>
                    <div className="text-slate-400 text-sm">Dark background with light text</div>
                  </div>
                </label>
                
                <label className="flex items-center p-3 bg-slate-700/50 rounded-lg cursor-not-allowed opacity-50">
                  <input
                    type="radio"
                    name="theme"
                    value="light"
                    disabled
                    className="mr-3"
                  />
                  <div>
                    <div className="text-white font-medium">Light (Coming Soon)</div>
                    <div className="text-slate-400 text-sm">Light background with dark text</div>
                  </div>
                </label>
                
                <label className="flex items-center p-3 bg-slate-700/50 rounded-lg cursor-not-allowed opacity-50">
                  <input
                    type="radio"
                    name="theme"
                    value="auto"
                    disabled
                    className="mr-3"
                  />
                  <div>
                    <div className="text-white font-medium">Auto (Coming Soon)</div>
                    <div className="text-slate-400 text-sm">Match system preferences</div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Notifications</h2>
            
            <div className="space-y-4">
              <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700 transition-colors">
                <div>
                  <div className="text-white font-medium">Email Notifications</div>
                  <div className="text-slate-400 text-sm">Receive updates about new content and recommendations</div>
                </div>
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="w-5 h-5"
                />
              </label>
            </div>
          </div>

          {/* Content Preferences */}
          <div className="bg-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Content</h2>
            
            <div className="space-y-4">
              <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700 transition-colors">
                <div>
                  <div className="text-white font-medium">AI Recommendations</div>
                  <div className="text-slate-400 text-sm">Show personalized content suggestions on your dashboard</div>
                </div>
                <input
                  type="checkbox"
                  checked={recommendationsEnabled}
                  onChange={(e) => setRecommendationsEnabled(e.target.checked)}
                  className="w-5 h-5"
                />
              </label>
            </div>
          </div>

          {/* Success/Error Message */}
          {message && (
            <div className={`p-4 rounded-lg ${
              message.type === 'success' 
                ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}>
              {message.text}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
            >
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
