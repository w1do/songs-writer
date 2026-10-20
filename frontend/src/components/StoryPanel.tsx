import { useState } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { ApiError, songsApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { useSpeechInput } from '@/hooks/useSpeechInput'

interface StoryPanelProps {
  songId: string
  story: string | null
  onSaved: (story: string | null) => void
}

const STORY_MAX_LENGTH = 10000

function appendText(current: string, addition: string): string {
  const trimmed = addition.trim()
  if (!trimmed) {
    return current
  }
  return current.trim() ? `${current.trimEnd()} ${trimmed}` : trimmed
}

export function StoryPanel({ songId, story, onSaved }: StoryPanelProps) {
  const savedStory = story ?? ''
  const [editing, setEditing] = useState(!savedStory)
  const [draft, setDraft] = useState(savedStory)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const speech = useSpeechInput((text) => setDraft((current) => appendText(current, text)))

  function startEditing() {
    setDraft(savedStory)
    setError(null)
    setEditing(true)
  }

  function cancelEditing() {
    speech.stop()
    setDraft(savedStory)
    setError(null)
    setEditing(false)
  }

  async function save() {
    speech.stop()
    const nextStory = draft.trim() ? draft : null
    setPending(true)
    setError(null)
    try {
      const updated = await songsApi.update(songId, { story: nextStory })
      onSaved(updated.story)
      setDraft(updated.story ?? '')
      setEditing(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось сохранить историю.')
    } finally {
      setPending(false)
    }
  }

  function toggleMic() {
    if (speech.listening) {
      speech.stop()
    } else {
      speech.start()
    }
  }

  const micButton = speech.supported && (
    <Button
      variant={speech.listening ? 'destructive' : 'outline'}
      size="sm"
      className="gap-2"
      aria-pressed={speech.listening}
      disabled={pending}
      onClick={toggleMic}
    >
      {speech.listening ? <MicOff className="size-4" /> : <Mic className="size-4" />}
      {speech.listening ? 'Остановить запись' : 'Надиктовать'}
    </Button>
  )

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>История песни</CardTitle>
        <CardDescription>
          Расскажите, про что песня. Историю можно надиктовать голосом или написать вручную.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {editing ? (
          <>
            <Textarea
              aria-label="История песни"
              value={draft}
              maxLength={STORY_MAX_LENGTH}
              placeholder="Например: история о том, как герой возвращается в родной город..."
              className="min-h-28"
              disabled={pending}
              onChange={(event) => setDraft(event.target.value)}
            />
            {speech.listening && speech.transcript && (
              <p className="text-xs text-muted-foreground">Распознаётся: {speech.transcript}</p>
            )}
            {speech.error && (
              <p role="alert" className="text-sm text-destructive">
                {speech.error}
              </p>
            )}
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              {micButton}
              <Button size="sm" disabled={pending} onClick={save}>
                {pending ? 'Сохранение...' : 'Сохранить'}
              </Button>
              {savedStory && (
                <Button variant="ghost" size="sm" disabled={pending} onClick={cancelEditing}>
                  Отмена
                </Button>
              )}
            </div>
          </>
        ) : (
          <>
            <p className="line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground">{savedStory}</p>
            <div>
              <Button variant="outline" size="sm" onClick={startEditing}>
                Изменить историю
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
