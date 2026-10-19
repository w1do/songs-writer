import { useEffect, useState } from 'react'
import { songsApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'

interface ExportDialogProps {
  songId: string
  onClose: () => void
}

export function ExportDialog({ songId, onClose }: ExportDialogProps) {
  const [json, setJson] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    songsApi
      .exportData(songId)
      .then((data) => {
        if (active) {
          setJson(JSON.stringify(data, null, 2))
        }
      })
      .catch(() => {
        if (active) {
          setError('Не удалось загрузить данные для экспорта')
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [songId])

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(json)
      setError(null)
      setMessage('JSON скопирован')
    } catch {
      setMessage(null)
      setError('Не удалось скопировать JSON')
    }
  }

  function downloadJson() {
    const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `song-${songId}.json`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Экспорт песни</CardTitle>
          <CardDescription>Данные берутся из сохранённой версии песни</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {loading && <p className="text-sm text-muted-foreground">Загрузка...</p>}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Textarea readOnly aria-label="JSON экспорта" className="min-h-64 font-mono text-xs" value={json} />
          {message && <p className="text-xs text-muted-foreground">{message}</p>}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="outline" size="sm" disabled={!json} onClick={copyJson}>
              Copy JSON
            </Button>
            <Button variant="outline" size="sm" disabled={!json} onClick={downloadJson}>
              Download .json
            </Button>
            <Button size="sm" onClick={onClose}>
              Закрыть
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
