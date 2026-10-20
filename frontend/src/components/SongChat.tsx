import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Mic, MicOff, Send, Sparkles } from 'lucide-react'
import { ApiError, aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { useSpeechInput } from '@/hooks/useSpeechInput'
import type { ChatMessage } from '@/types'

interface SongChatProps {
  songId: string
  onLyricsChange: (lyrics: string) => void
}

const CREATE_SONG_PROMPT =
  'Придумай песню по моей истории, теме, жанру и пресету. Выстрой текст по секциям с тегами.'

function appendText(current: string, addition: string): string {
  const trimmed = addition.trim()
  if (!trimmed) {
    return current
  }
  return current.trim() ? `${current.trimEnd()} ${trimmed}` : trimmed
}

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Не удалось получить ответ ИИ. Попробуйте ещё раз.'
}

export function SongChat({ songId, onLyricsChange }: SongChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const speech = useSpeechInput((text) => setInput((current) => appendText(current, text)))

  useEffect(() => {
    let active = true
    aiApi.listMessages(songId).then(
      (loaded) => {
        if (active) {
          setMessages(loaded)
          setLoading(false)
        }
      },
      (err: unknown) => {
        if (active) {
          setError(errorMessage(err))
          setLoading(false)
        }
      }
    )
    return () => {
      active = false
    }
  }, [songId])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, pending])

  async function send(text: string) {
    const message = text.trim()
    if (!message || pending) {
      return
    }
    speech.stop()
    setPending(true)
    setError(null)
    try {
      const response = await aiApi.chat(songId, message)
      setMessages((current) => [...current, ...response.messages])
      if (response.lyrics !== null) {
        onLyricsChange(response.lyrics)
      }
      setInput((current) => (current.trim() === message ? '' : current))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setPending(false)
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send(input)
    }
  }

  function toggleMic() {
    if (speech.listening) {
      speech.stop()
    } else {
      speech.start()
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Чат с ИИ</CardTitle>
        <CardDescription>
          ИИ учитывает историю, тему, жанр и пресет. Опишите, что изменить в тексте, голосом или текстом.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Button className="gap-2" disabled={pending || loading} onClick={() => send(CREATE_SONG_PROMPT)}>
            <Sparkles className="size-4" />
            Придумать песню по AI
          </Button>
        </div>
        <div
          ref={listRef}
          role="log"
          aria-live="polite"
          className="flex max-h-96 min-h-24 flex-col gap-3 overflow-y-auto rounded-md border p-3"
        >
          {loading && <p className="text-sm text-muted-foreground">Загрузка сообщений...</p>}
          {!loading && messages.length === 0 && (
            <p className="text-sm text-muted-foreground">Сообщений пока нет. Начните с истории или нажмите кнопку выше.</p>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === 'user'
                  ? 'ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground'
                  : 'mr-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-muted px-3 py-2 text-sm'
              }
            >
              {message.content}
            </div>
          ))}
          {pending && <p className="mr-auto text-sm text-muted-foreground">ИИ думает...</p>}
        </div>
        {speech.listening && speech.transcript && (
          <p className="text-xs text-muted-foreground">Распознаётся: {speech.transcript}</p>
        )}
        {(error || speech.error) && (
          <p role="alert" className="text-sm text-destructive">
            {error ?? speech.error}
          </p>
        )}
        <div className="flex items-end gap-2">
          <Textarea
            aria-label="Сообщение для ИИ"
            value={input}
            placeholder="Например: добавь припев про дорогу домой"
            className="min-h-16"
            disabled={pending}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          {speech.supported && (
            <Button
              variant={speech.listening ? 'destructive' : 'outline'}
              size="icon"
              aria-label={speech.listening ? 'Остановить запись' : 'Записать голосом'}
              aria-pressed={speech.listening}
              disabled={pending}
              onClick={toggleMic}
            >
              {speech.listening ? <MicOff className="size-4" /> : <Mic className="size-4" />}
            </Button>
          )}
          <Button
            size="icon"
            aria-label="Отправить"
            disabled={pending || !input.trim()}
            onClick={() => send(input)}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
