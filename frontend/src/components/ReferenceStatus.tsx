import { useReferenceStatus } from '@/hooks/useReferenceStatus'
import type { ReferenceAnalysisStatus } from '@/types'

interface ReferenceStatusProps {
  songId: string
  onDone: () => void
}

const STATUS_LABELS: Record<ReferenceAnalysisStatus, string> = {
  pending: 'Анализ референса...',
  done: 'Анализ готов, пресет доступен',
  failed: 'Не удалось проанализировать референс',
}

export function ReferenceStatus({ songId, onDone }: ReferenceStatusProps) {
  const status = useReferenceStatus(songId, onDone)

  return (
    <p role="status" className="text-sm text-muted-foreground">
      {STATUS_LABELS[status]}
    </p>
  )
}
