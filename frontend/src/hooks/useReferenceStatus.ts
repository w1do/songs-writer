import { useEffect, useRef, useState } from 'react'
import { songsApi } from '@/api'
import type { ReferenceAnalysisStatus } from '@/types'

const POLL_INTERVAL_MS = 2000

export function useReferenceStatus(songId: string, onDone: () => void): ReferenceAnalysisStatus {
  const [status, setStatus] = useState<ReferenceAnalysisStatus>('pending')
  const onDoneRef = useRef(onDone)

  useEffect(() => {
    onDoneRef.current = onDone
  }, [onDone])

  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      try {
        const song = await songsApi.get(songId)
        if (!active) {
          return
        }
        if (song.analysis_status === 'done') {
          setStatus('done')
          onDoneRef.current()
          return
        }
        if (song.analysis_status === 'failed') {
          setStatus('failed')
          return
        }
        timer = setTimeout(poll, POLL_INTERVAL_MS)
      } catch {
        if (active) {
          setStatus('failed')
        }
      }
    }

    void poll()
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [songId])

  return status
}
