import { useState } from 'react'
import { aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Sparkles } from 'lucide-react'
import type { AnalysisResult, Preset, Song } from '@/types'

interface AnalysisSidebarProps {
  songId: string
  analysis: Record<string, unknown> | null
  preset: Preset | null
  onAnalysisChange: (analysis: Record<string, unknown>) => void
  onSongUpdate: (song: Song) => void
}

function parseStructure(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function AnalysisSidebar({ songId, analysis, preset, onAnalysisChange, onSongUpdate }: AnalysisSidebarProps) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const data = (analysis ?? {}) as Partial<AnalysisResult>
  const structure = Array.isArray(data.structure) ? data.structure : []

  function updateField(patch: Partial<AnalysisResult>) {
    onAnalysisChange({ ...data, ...patch })
  }

  async function handleAnalyze() {
    setPending(true)
    setError(null)
    try {
      onSongUpdate(await aiApi.analyzeIdea(songId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось проанализировать идею')
    } finally {
      setPending(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" />
          Анализ идеи
        </CardTitle>
        <CardDescription>
          Пресет: {preset ? `${preset.name} (${preset.genre})` : 'не выбран'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-xs text-muted-foreground">
          AI разбирает идею и предлагает тему, жанр, темп и структуру. Значения можно поправить вручную.
        </p>
        <Button className="gap-2" disabled={pending} onClick={handleAnalyze}>
          <Sparkles className="size-4" />
          {pending ? 'Анализ...' : 'Проанализировать идею'}
        </Button>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-medium sm:col-span-2">
            Тема
            <Input value={data.theme ?? ''} onChange={(event) => updateField({ theme: event.target.value })} />
            <span className="font-normal text-muted-foreground">Главная мысль песни, о чём она.</span>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Жанр
            <Input value={data.genre ?? ''} onChange={(event) => updateField({ genre: event.target.value })} />
            <span className="font-normal text-muted-foreground">Стиль звучания, например rap или synth-pop.</span>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Эмоция
            <Input value={data.emotion ?? ''} onChange={(event) => updateField({ emotion: event.target.value })} />
            <span className="font-normal text-muted-foreground">Настроение трека: злость, грусть, радость.</span>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            BPM
            <Input
              type="number"
              value={data.bpm ?? ''}
              onChange={(event) =>
                updateField({ bpm: event.target.value === '' ? undefined : Number(event.target.value) })
              }
            />
            <span className="font-normal text-muted-foreground">Темп: ударов в минуту, обычно 60–180.</span>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Энергия
            <Input
              type="number"
              value={data.energy ?? ''}
              onChange={(event) =>
                updateField({ energy: event.target.value === '' ? undefined : Number(event.target.value) })
              }
            />
            <span className="font-normal text-muted-foreground">Напор трека от 0 (тихо) до 1 (очень драйвово).</span>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium sm:col-span-2">
            Структура (через запятую)
            <Input
              key={structure.join(',')}
              defaultValue={structure.join(', ')}
              onBlur={(event) => updateField({ structure: parseStructure(event.target.value) })}
            />
            <span className="font-normal text-muted-foreground">Порядок разделов, например: intro, verse, chorus, outro.</span>
          </label>
        </div>
      </CardContent>
    </Card>
  )
}
