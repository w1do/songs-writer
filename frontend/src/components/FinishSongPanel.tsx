import { useState } from 'react'
import { aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface FinishSongPanelProps {
  songId: string
}

export function FinishSongPanel({ songId }: FinishSongPanelProps) {
  const [comments, setComments] = useState<string[] | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFinish() {
    setPending(true)
    setError(null)
    try {
      const result = await aiApi.finishSong(songId)
      setComments(result.comments)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось получить комментарии')
    } finally {
      setPending(false)
    }
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Завершение песни</CardTitle>
        <CardDescription>Комментарии не меняют текст песни</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Button variant="outline" size="sm" disabled={pending} onClick={handleFinish}>
          {pending ? 'Анализ...' : 'Завершить песню'}
        </Button>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {comments && (
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm">
            {comments.map((comment, index) => (
              <li key={index}>{comment}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
