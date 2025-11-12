import { useState, useRef, useCallback } from 'react'

interface DeletionProgress {
  current: number
  total: number
  deleted: number
  failed: number
  currentItem?: string
  status: 'processing' | 'completed' | 'error' | 'idle'
  message?: string
}

export function useDeletionProgress(apiUrl: string, accessToken: string) {
  const [progress, setProgress] = useState<DeletionProgress>({
    current: 0,
    total: 0,
    deleted: 0,
    failed: 0,
    status: 'idle'
  })
  
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  
  const startPolling = useCallback(() => {
    // Poll every 1 second
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${apiUrl}/api/admin/deletion/progress`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          setProgress(data)
          
          // Stop polling when completed or error
          if (data.status === 'completed' || data.status === 'error') {
            stopPolling()
          }
        }
      } catch (error) {
        console.error('Error polling progress:', error)
      }
    }, 1000)
  }, [apiUrl, accessToken])
  
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])
  
  const reset = useCallback(() => {
    stopPolling()
    setProgress({
      current: 0,
      total: 0,
      deleted: 0,
      failed: 0,
      status: 'idle'
    })
  }, [stopPolling])
  
  return { progress, startPolling, stopPolling, reset }
}
