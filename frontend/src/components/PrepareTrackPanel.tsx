import { useState } from 'react'
import { ApiError, aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import type { GenerationSettings, Song, TrackSettings } from '@/types'

interface PrepareTrackPanelProps {
  songId: string
  trackSettings: TrackSettings | null
  generationSettings: GenerationSettings | null
  onPrepared: (song: Song) => void
  onTrackSettingsChange: (settings: TrackSettings) => void
  onGenerationSettingsChange: (settings: GenerationSettings) => void
}

function stringifyGenerationSettings(settings: GenerationSettings | null): string {
  return settings && Object.keys(settings).length > 0 ? JSON.stringify(settings, null, 2) : ''
}

function parseGenerationSettings(text: string): GenerationSettings | null {
  if (!text.trim()) {
    return {}
  }
  try {
    const parsed: unknown = JSON.parse(text)
    return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed) ? (parsed as GenerationSettings) : null
  } catch {
    return null
  }
}

export function PrepareTrackPanel({
  songId,
  trackSettings,
  generationSettings,
  onPrepared,
  onTrackSettingsChange,
  onGenerationSettingsChange,
}: PrepareTrackPanelProps) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generationText, setGenerationText] = useState(() => stringifyGenerationSettings(generationSettings))
  const [generationError, setGenerationError] = useState<string | null>(null)

  async function handlePrepare() {
    setPending(true)
    setError(null)
    try {
      const song = await aiApi.prepareTrack(songId)
      onPrepared(song)
      setGenerationText(stringifyGenerationSettings(song.generation_settings))
      setGenerationError(null)
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 502
          ? 'AI-сервис не смог подготовить трек. Данные не изменены.'
          : 'Не удалось подготовить трек. Данные не изменены.',
      )
    } finally {
      setPending(false)
    }
  }

  function handleGenerationChange(text: string) {
    setGenerationText(text)
    const parsed = parseGenerationSettings(text)
    if (parsed === null) {
      setGenerationError('Generation Settings должны быть JSON-объектом. Сохранены последние корректные значения.')
      return
    }
    setGenerationError(null)
    onGenerationSettingsChange(parsed)
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Prepare Track: данные для генерации музыки</CardTitle>
        <CardDescription>
          Последний шаг. Здесь текст песни превращается в описание для внешнего генератора музыки: стиль,
          что исключить, манера исполнения и технические параметры. Сам текст на этом шаге не меняется.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <Button variant="outline" size="sm" disabled={pending} onClick={handlePrepare}>
            {pending ? 'Подготовка...' : 'Заполнить по песне (AI)'}
          </Button>
          <p className="text-xs text-muted-foreground">
            AI прочитает идею, анализ и текст и заполнит поля ниже. Значения, которые вы ввели вручную, будут заменены.
          </p>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <label className="flex flex-col gap-1 text-xs font-medium">
          Style Prompt: жанр, настроение, инструменты, темп
          <span className="font-normal text-muted-foreground">Например: «синти-поп, 120 BPM, мягкий бас, женский вокал»</span>
          <Textarea
            value={trackSettings?.style_prompt ?? ''}
            onChange={(event) => onTrackSettingsChange({ ...trackSettings, style_prompt: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Negative Style: что не должно звучать
          <span className="font-normal text-muted-foreground">Например: «гитарные соло, медленный темп, рэп»</span>
          <Textarea
            value={trackSettings?.negative_style_prompt ?? ''}
            onChange={(event) =>
              onTrackSettingsChange({ ...trackSettings, negative_style_prompt: event.target.value })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Performance: как исполнять вокал
          <span className="font-normal text-muted-foreground">Например: «мягко в куплетах, мощно в припеве»</span>
          <Textarea
            value={trackSettings?.performance ?? ''}
            onChange={(event) => onTrackSettingsChange({ ...trackSettings, performance: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Generation Settings: технические параметры в JSON
          <span className="font-normal text-muted-foreground">Необязательно. Пустое значение эквивалентно {'{}'}.</span>
          <Textarea
            className="font-mono text-xs"
            value={generationText}
            aria-invalid={generationError !== null}
            onChange={(event) => handleGenerationChange(event.target.value)}
          />
        </label>
        {generationError && (
          <p role="alert" className="text-sm text-destructive">
            {generationError}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
