'use client'

import { useEffect, useState } from 'react'

interface DeletionProgress {
  current: number
  total: number
  deleted: number
  failed: number
  currentItem?: string
  status: 'processing' | 'completed' | 'error'
  message?: string
}

interface DeletionProgressModalProps {
  isOpen: boolean
  onClose: () => void
  progress: DeletionProgress
}

export default function DeletionProgressModal({ 
  isOpen, 
  onClose,
  progress
}: DeletionProgressModalProps) {
  const percentComplete = progress.total > 0 
    ? Math.round((progress.current / progress.total) * 100) 
    : 0

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg shadow-2xl p-8 max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">
            Deletion In Progress
          </h2>
          <p className="text-slate-400">
            {progress.status === 'processing' && 'Please wait while we process your request...'}
            {progress.status === 'completed' && '✅ Process completed successfully!'}
            {progress.status === 'error' && '❌ An error occurred during processing'}
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-slate-400 mb-2">
            <span>Progress</span>
            <span>{progress.current} / {progress.total} items ({percentComplete}%)</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                progress.status === 'error' ? 'bg-red-500' :
                progress.status === 'completed' ? 'bg-green-500' :
                'bg-blue-500'
              }`}
              style={{ width: `${percentComplete}%` }}
            />
          </div>
        </div>

        {/* Current Item */}
        {progress.currentItem && progress.status === 'processing' && (
          <div className="mb-6 p-4 bg-slate-700 rounded-lg">
            <div className="text-sm text-slate-400 mb-1">Currently processing:</div>
            <div className="text-white font-medium truncate">{progress.currentItem}</div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-sm text-slate-400 mb-1">Deleted</div>
            <div className="text-2xl font-bold text-green-400">{progress.deleted}</div>
          </div>
          <div className="bg-slate-700 rounded-lg p-4">
            <div className="text-sm text-slate-400 mb-1">Failed</div>
            <div className="text-2xl font-bold text-red-400">{progress.failed}</div>
          </div>
        </div>

        {/* Status Message */}
        {progress.message && (
          <div className={`mb-6 p-4 rounded-lg ${
            progress.status === 'error' ? 'bg-red-900/30 text-red-400' :
            progress.status === 'completed' ? 'bg-green-900/30 text-green-400' :
            'bg-blue-900/30 text-blue-400'
          }`}>
            {progress.message}
          </div>
        )}

        {/* Loading Spinner */}
        {progress.status === 'processing' && (
          <div className="flex justify-center mb-6">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          {progress.status === 'processing' ? (
            <button
              disabled
              className="px-6 py-2 bg-slate-600 text-slate-400 rounded-lg cursor-not-allowed"
            >
              Processing...
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Hook to manage progress updates
export function useDeletionProgress(onProgressUpdate?: (progress: DeletionProgress) => void) {
  const [progress, setProgress] = useState<DeletionProgress>({
    current: 0,
    total: 0,
    deleted: 0,
    failed: 0,
    status: 'processing'
  })

  const updateProgress = (update: Partial<DeletionProgress>) => {
    setProgress(prev => {
      const newProgress = { ...prev, ...update }
      onProgressUpdate?.(newProgress)
      return newProgress
    })
  }

  const reset = () => {
    setProgress({
      current: 0,
      total: 0,
      deleted: 0,
      failed: 0,
      status: 'processing'
    })
  }

  return { progress, updateProgress, reset }
}
