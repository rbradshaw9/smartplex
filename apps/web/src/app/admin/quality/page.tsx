'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { Database } from '@smartplex/db'

interface QualityBreakdown {
  video_resolution: string | null
  video_codec: string | null
  container: string | null
  item_count: number
  total_gb: number
  avg_bitrate_kbps: number | null
  avg_size_gb: number
}

interface QualityAnalysis {
  summary: {
    total_items: number
    total_gb: number
    unique_combinations: number
  }
  by_codec: Record<string, { item_count: number; total_gb: number; avg_bitrate_kbps: number }>
  by_resolution: Record<string, { item_count: number; total_gb: number }>
  insights: {
    h264_to_hevc_savings_gb: number
    h264_percentage: number
    hevc_percentage: number
  }
  detailed_breakdown: QualityBreakdown[]
}

interface InaccessibleFile {
  id: string
  title: string
  type: string
  file_path: string | null
  file_size_bytes: number | null
  size_gb: number
  added_at: string
  updated_at: string
}

interface InaccessibleFilesResponse {
  total_inaccessible: number
  total_wasted_gb: number
  files: InaccessibleFile[]
}

export default function QualityDashboardPage() {
  const router = useRouter()
  const [supabase] = useState(() => createClientComponentClient<Database>())
  const [loading, setLoading] = useState(true)
  const [qualityData, setQualityData] = useState<QualityAnalysis | null>(null)
  const [inaccessibleFiles, setInaccessibleFiles] = useState<InaccessibleFilesResponse | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'inaccessible'>('overview')

  useEffect(() => {
    checkAuth()
    loadQualityData()
    loadInaccessibleFiles()
  }, [])

  const checkAuth = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      router.push('/login')
      return
    }
  }

  const loadQualityData = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch('/api/admin/system/storage/quality-analysis', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to load quality data')
      }

      const data = await response.json()
      setQualityData(data)
    } catch (err) {
      console.error('Error loading quality data:', err)
      setError('Failed to load quality analysis')
    }
  }

  const loadInaccessibleFiles = async () => {
    try {
      setLoading(true)
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch('/api/admin/system/storage/inaccessible-files', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to load inaccessible files')
      }

      const data = await response.json()
      setInaccessibleFiles(data)
    } catch (err) {
      console.error('Error loading inaccessible files:', err)
      setError('Failed to load inaccessible files')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSelected = async () => {
    if (selectedFiles.size === 0) {
      setError('No files selected')
      return
    }

    if (!confirm(`Delete ${selectedFiles.size} inaccessible file(s)? This will permanently remove them from your library.`)) {
      return
    }

    try {
      setDeleting(true)
      setError('')
      setSuccessMessage('')

      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        throw new Error('Not authenticated')
      }

      const response = await fetch('/api/admin/system/storage/delete-media', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          media_item_ids: Array.from(selectedFiles),
          delete_from_filesystem: true,
          cascade_to_arr: true,
          reason: 'inaccessible_file_cleanup'
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete files')
      }

      const result = await response.json()
      setSuccessMessage(`Deleted ${result.deleted} file(s), ${result.failed} failed. Freed ${result.total_size_gb.toFixed(2)} GB`)
      setSelectedFiles(new Set())
      
      // Reload data
      await loadInaccessibleFiles()
      await loadQualityData()
    } catch (err) {
      console.error('Error deleting files:', err)
      setError(err instanceof Error ? err.message : 'Failed to delete files')
    } finally {
      setDeleting(false)
    }
  }

  const toggleFileSelection = (fileId: string) => {
    const newSelection = new Set(selectedFiles)
    if (newSelection.has(fileId)) {
      newSelection.delete(fileId)
    } else {
      newSelection.add(fileId)
    }
    setSelectedFiles(newSelection)
  }

  const selectAllFiles = () => {
    if (!inaccessibleFiles) return
    setSelectedFiles(new Set(inaccessibleFiles.files.map(f => f.id)))
  }

  const clearSelection = () => {
    setSelectedFiles(new Set())
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Loading quality analysis...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Storage Quality Dashboard</h1>
          <p className="text-slate-400">Analyze codec usage, identify optimization opportunities, and manage broken files</p>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-900/50 border border-red-700 rounded-lg">
            {error}
          </div>
        )}
        {successMessage && (
          <div className="mb-4 p-4 bg-green-900/50 border border-green-700 rounded-lg">
            {successMessage}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b border-slate-700">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'overview'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Quality Overview
            </button>
            <button
              onClick={() => setActiveTab('inaccessible')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'inaccessible'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Inaccessible Files
              {inaccessibleFiles && inaccessibleFiles.total_inaccessible > 0 && (
                <span className="ml-2 px-2 py-0.5 text-xs bg-red-600 rounded-full">
                  {inaccessibleFiles.total_inaccessible}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && qualityData && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-slate-400 text-sm font-medium mb-2">Total Items</h3>
                <p className="text-3xl font-bold">{qualityData.summary.total_items.toLocaleString()}</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-slate-400 text-sm font-medium mb-2">Total Storage</h3>
                <p className="text-3xl font-bold">{qualityData.summary.total_gb.toFixed(2)} GB</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-slate-400 text-sm font-medium mb-2">H.264 → HEVC Savings</h3>
                <p className="text-3xl font-bold text-green-400">
                  {qualityData.insights.h264_to_hevc_savings_gb.toFixed(2)} GB
                </p>
                <p className="text-xs text-slate-400 mt-1">Potential savings (40% estimate)</p>
              </div>
            </div>

            {/* Codec Breakdown */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-bold mb-4">Codec Distribution</h2>
              <div className="space-y-4">
                {Object.entries(qualityData.by_codec).map(([codec, data]) => {
                  const percentage = (data.total_gb / qualityData.summary.total_gb) * 100
                  return (
                    <div key={codec}>
                      <div className="flex justify-between mb-2">
                        <span className="font-medium uppercase">{codec || 'Unknown'}</span>
                        <span className="text-slate-400">
                          {data.item_count} items · {data.total_gb.toFixed(2)} GB ({percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            codec === 'h264' ? 'bg-yellow-500' : 
                            codec === 'hevc' ? 'bg-green-500' : 
                            'bg-blue-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Resolution Breakdown */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-bold mb-4">Resolution Distribution</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(qualityData.by_resolution).map(([resolution, data]) => (
                  <div key={resolution} className="bg-slate-700 rounded-lg p-4">
                    <h3 className="text-2xl font-bold mb-1">{resolution || 'Unknown'}</h3>
                    <p className="text-slate-400 text-sm">{data.item_count} items</p>
                    <p className="text-lg font-semibold mt-2">{data.total_gb.toFixed(2)} GB</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Detailed Breakdown Table */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-bold mb-4">Detailed Breakdown</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left border-b border-slate-700">
                    <tr>
                      <th className="pb-3 font-medium text-slate-400">Resolution</th>
                      <th className="pb-3 font-medium text-slate-400">Codec</th>
                      <th className="pb-3 font-medium text-slate-400">Container</th>
                      <th className="pb-3 font-medium text-slate-400 text-right">Items</th>
                      <th className="pb-3 font-medium text-slate-400 text-right">Total GB</th>
                      <th className="pb-3 font-medium text-slate-400 text-right">Avg GB/Item</th>
                      <th className="pb-3 font-medium text-slate-400 text-right">Avg Bitrate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {qualityData.detailed_breakdown.map((item, idx) => (
                      <tr key={idx} className="border-b border-slate-700/50">
                        <td className="py-3">{item.video_resolution || 'Unknown'}</td>
                        <td className="py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            item.video_codec === 'h264' ? 'bg-yellow-900/50 text-yellow-300' :
                            item.video_codec === 'hevc' ? 'bg-green-900/50 text-green-300' :
                            'bg-blue-900/50 text-blue-300'
                          }`}>
                            {item.video_codec?.toUpperCase() || 'Unknown'}
                          </span>
                        </td>
                        <td className="py-3">{item.container?.toUpperCase() || 'Unknown'}</td>
                        <td className="py-3 text-right">{item.item_count}</td>
                        <td className="py-3 text-right">{item.total_gb.toFixed(2)}</td>
                        <td className="py-3 text-right">{item.avg_size_gb.toFixed(2)}</td>
                        <td className="py-3 text-right">
                          {item.avg_bitrate_kbps ? `${Math.round(item.avg_bitrate_kbps)} kbps` : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Insights */}
            <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-lg p-6 border border-blue-700/50">
              <h2 className="text-xl font-bold mb-4 flex items-center">
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Optimization Insights
              </h2>
              <div className="space-y-3 text-slate-300">
                <p>
                  • Your library contains <strong>{qualityData.insights.h264_percentage}%</strong> H.264 content
                  and <strong>{qualityData.insights.hevc_percentage}%</strong> HEVC content.
                </p>
                <p>
                  • Converting H.264 content to HEVC could save approximately{' '}
                  <strong className="text-green-400">{qualityData.insights.h264_to_hevc_savings_gb.toFixed(2)} GB</strong>{' '}
                  (40% compression improvement).
                </p>
                <p>
                  • Consider using tools like <strong>Tdarr</strong> or <strong>HandBrake</strong> for automated transcoding.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Inaccessible Files Tab */}
        {activeTab === 'inaccessible' && inaccessibleFiles && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-slate-400 text-sm font-medium mb-2">Inaccessible Files</h3>
                <p className="text-3xl font-bold text-red-400">{inaccessibleFiles.total_inaccessible}</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-slate-400 text-sm font-medium mb-2">Wasted Storage</h3>
                <p className="text-3xl font-bold text-red-400">{inaccessibleFiles.total_wasted_gb.toFixed(2)} GB</p>
              </div>
            </div>

            {/* Actions */}
            {inaccessibleFiles.files.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-slate-400">
                    {selectedFiles.size} of {inaccessibleFiles.files.length} selected
                  </span>
                  <button
                    onClick={selectAllFiles}
                    className="text-blue-400 hover:text-blue-300 text-sm"
                  >
                    Select All
                  </button>
                  {selectedFiles.size > 0 && (
                    <button
                      onClick={clearSelection}
                      className="text-slate-400 hover:text-white text-sm"
                    >
                      Clear Selection
                    </button>
                  )}
                </div>
                <button
                  onClick={handleDeleteSelected}
                  disabled={selectedFiles.size === 0 || deleting}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg font-medium transition-colors"
                >
                  {deleting ? 'Deleting...' : `Delete Selected (${selectedFiles.size})`}
                </button>
              </div>
            )}

            {/* Files List */}
            {inaccessibleFiles.files.length === 0 ? (
              <div className="bg-slate-800 rounded-lg p-12 text-center border border-slate-700">
                <svg className="w-16 h-16 mx-auto mb-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-xl font-bold mb-2">All Files Accessible</h3>
                <p className="text-slate-400">No broken or missing files detected in your library.</p>
              </div>
            ) : (
              <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-700/50 text-left">
                    <tr>
                      <th className="p-4 w-12"></th>
                      <th className="p-4 font-medium">Title</th>
                      <th className="p-4 font-medium">Type</th>
                      <th className="p-4 font-medium">File Path</th>
                      <th className="p-4 font-medium text-right">Size</th>
                      <th className="p-4 font-medium">Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inaccessibleFiles.files.map((file) => (
                      <tr key={file.id} className="border-t border-slate-700 hover:bg-slate-700/30">
                        <td className="p-4">
                          <input
                            type="checkbox"
                            checked={selectedFiles.has(file.id)}
                            onChange={() => toggleFileSelection(file.id)}
                            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500"
                          />
                        </td>
                        <td className="p-4 font-medium">{file.title}</td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded text-xs ${
                            file.type === 'movie' ? 'bg-purple-900/50 text-purple-300' : 'bg-blue-900/50 text-blue-300'
                          }`}>
                            {file.type}
                          </span>
                        </td>
                        <td className="p-4 text-slate-400 text-xs font-mono truncate max-w-md">
                          {file.file_path || 'Unknown'}
                        </td>
                        <td className="p-4 text-right">{file.size_gb.toFixed(2)} GB</td>
                        <td className="p-4 text-slate-400">
                          {new Date(file.added_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
