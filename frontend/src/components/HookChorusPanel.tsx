import { useState } from 'react'
import { aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface HookChorusPanelProps {
  songId: string
  onInsert: (block: string) => void
}

export function HookChorusPanel({ songId, onInsert }: HookChorusPanelProps) {
  const [hooks, setHooks] = useState<string[]>([])
  const [choruses, setChoruses] = useState<string[][]>([])
  const [loading, setLoading] = useState<'hook' | 'chorus' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function createHook() {
    setLoading('hook')
    setError(null)
    try {
      const result = await aiApi.createHook(songId)
      setHooks(result.variants)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать хук')
    } finally {
      setLoading(null)
    }
  }

  async function createChorus() {
    setLoading('chorus')
    setError(null)
    try {
      const result = await aiApi.createChorus(songId)
      setChoruses(result.variants)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать припев')
    } finally {
      setLoading(null)
    }
  }

  function insertHook(variant: string) {
    onInsert(`[HOOK]\n${variant}`)
    setHooks([])
  }

  function insertChorus(lines: string[]) {
    onInsert(`[CHORUS]\n${lines.join('\n')}`)
    setChoruses([])
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Хук и припев</CardTitle>
        <CardDescription>Вариант добавляется в конец текста только по кнопке</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={loading !== null} onClick={createHook}>
            {loading === 'hook' ? 'Создание...' : 'Создать хук'}
          </Button>
          <Button variant="outline" size="sm" disabled={loading !== null} onClick={createChorus}>
            {loading === 'chorus' ? 'Создание...' : 'Создать припев'}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {hooks.map((variant, index) => (
          <div key={`hook-${index}`} className="flex items-start justify-between gap-3 rounded-lg border p-3 text-sm">
            <p className="whitespace-pre-wrap">{variant}</p>
            <Button size="sm" onClick={() => insertHook(variant)}>
              Вставить
            </Button>
          </div>
        ))}
        {choruses.map((lines, index) => (
          <div key={`chorus-${index}`} className="flex items-start justify-between gap-3 rounded-lg border p-3 text-sm">
            <p className="whitespace-pre-wrap">{lines.join('\n')}</p>
            <Button size="sm" onClick={() => insertChorus(lines)}>
              Вставить
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
