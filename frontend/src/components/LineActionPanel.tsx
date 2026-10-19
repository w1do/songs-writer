import { useState } from 'react'
import { aiApi } from '@/api'
import type { TextRange } from '@/components/LyricsEditor'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { LineActionType } from '@/types'

const ACTIONS: { type: LineActionType; label: string }[] = [
  { type: 'variants', label: 'Варианты' },
  { type: 'continue', label: 'Продолжить' },
  { type: 'rewrite', label: 'Переписать' },
  { type: 'rhyme', label: 'Рифма' },
  { type: 'flow', label: 'Флоу' },
  { type: 'vocal', label: 'Вокал' },
]

interface PendingResult {
  target: TextRange
  original: string
  prefix: string
  variants: string[]
  note: string | null
}

function findSectionBounds(lyrics: string, position: number): TextRange {
  const headers = [...lyrics.matchAll(/^\[[^\]\n]+\]\s*$/gm)].map((match) => match.index ?? 0)
  const start = headers.filter((index) => index <= position).pop() ?? 0
  const end = headers.find((index) => index > position) ?? lyrics.length
  return { start, end }
}

interface LineActionPanelProps {
  songId: string
  lyrics: string
  range: TextRange
  onReplace: (range: TextRange, text: string) => void
}

export function LineActionPanel({ songId, lyrics, range, onReplace }: LineActionPanelProps) {
  const [pending, setPending] = useState<PendingResult | null>(null)
  const [loadingAction, setLoadingAction] = useState<LineActionType | null>(null)
  const [sectionLoading, setSectionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasSelection = range.end > range.start

  function resolveTarget(): { target: TextRange; line: string; selection: string | null } {
    const lineStart = range.start > 0 ? lyrics.lastIndexOf('\n', range.start - 1) + 1 : 0
    const lineBreak = lyrics.indexOf('\n', range.start)
    const lineEnd = lineBreak === -1 ? lyrics.length : lineBreak
    const line = lyrics.slice(lineStart, lineEnd)

    if (hasSelection) {
      return {
        target: range,
        line,
        selection: lyrics.slice(range.start, range.end),
      }
    }
    return {
      target: { start: lineStart, end: lineEnd },
      line,
      selection: null,
    }
  }

  async function runAction(action: LineActionType) {
    const { target, line, selection } = resolveTarget()
    if (!line.trim()) {
      setError('Выделите строку или фрагмент с текстом')
      return
    }

    setLoadingAction(action)
    setError(null)
    setPending(null)
    try {
      const result = await aiApi.lineAction(songId, { action, line, selection })
      setPending({
        target,
        original: lyrics.slice(target.start, target.end),
        prefix: '',
        variants: result.variants,
        note: result.note,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить действие')
    } finally {
      setLoadingAction(null)
    }
  }

  async function runContinueSection() {
    const section = findSectionBounds(lyrics, range.start)
    const text = lyrics.slice(section.start, section.end).trimEnd()
    if (!text.trim()) {
      setError('В этом разделе пока нет текста. Напишите хотя бы одну строку')
      return
    }

    setSectionLoading(true)
    setError(null)
    setPending(null)
    try {
      const result = await aiApi.continueSection(songId, text)
      setPending({
        target: { start: section.start, end: section.start + text.length },
        original: text,
        prefix: `${text}\n`,
        variants: result.variants,
        note: result.note,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось продолжить раздел')
    } finally {
      setSectionLoading(false)
    }
  }

  function applyVariant(variant: string) {
    if (!pending) {
      return
    }
    if (lyrics.slice(pending.target.start, pending.target.end) !== pending.original) {
      setError('Текст изменился после запроса. Запустите действие заново')
      setPending(null)
      return
    }
    onReplace(pending.target, pending.prefix + variant)
    setPending(null)
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>AI-действия для строки</CardTitle>
        <CardDescription>
          {hasSelection ? 'Будет использован выделенный фрагмент' : 'Будет использована строка с курсором'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <div>
            <Button size="sm" disabled={sectionLoading} onClick={runContinueSection}>
              {sectionLoading ? 'Запрос...' : 'Продолжить куплет'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Не нужно выделять строку: AI прочитает весь раздел вокруг курсора и предложит следующие строки. Вариант добавится в конец раздела.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {ACTIONS.map(({ type, label }) => (
            <Button
              key={type}
              size="sm"
              variant="outline"
              disabled={loadingAction !== null || sectionLoading}
              onClick={() => runAction(type)}
            >
              {loadingAction === type ? 'Запрос...' : label}
            </Button>
          ))}
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {pending && (
          <div className="flex flex-col gap-2">
            {pending.note && <p className="text-sm text-muted-foreground">{pending.note}</p>}
            {pending.variants.map((variant, index) => (
              <div key={index} className="flex items-start justify-between gap-3 rounded-lg border p-3 text-sm">
                <p className="whitespace-pre-wrap">{variant}</p>
                <Button size="sm" onClick={() => applyVariant(variant)}>
                  Применить
                </Button>
              </div>
            ))}
            <Button variant="ghost" size="sm" onClick={() => setPending(null)}>
              Скрыть
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
