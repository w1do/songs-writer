import { useEffect, useRef, useState } from 'react'
import { songsApi } from '@/api'
import type { SongUpdateInput } from '@/types'

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function useAutosave(songId: string, payload: SongUpdateInput, delay = 800): AutosaveStatus {
  const [status, setStatus] = useState<AutosaveStatus>('idle')
  const serialized = JSON.stringify(payload)
  const lastSaved = useRef(serialized)

  useEffect(() => {
    if (serialized === lastSaved.current) {
      return
    }

    const timer = window.setTimeout(() => {
      setStatus('saving')
      songsApi
        .update(songId, JSON.parse(serialized) as SongUpdateInput)
        .then(() => {
          lastSaved.current = serialized
          setStatus('saved')
        })
        .catch(() => setStatus('error'))
    }, delay)

    return () => window.clearTimeout(timer)
  }, [songId, serialized, delay])

  return status
}
