import { useState } from 'react'
import { aiApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface LyricsDraftPanelProps {
  songId: string
  hasAnalysis: boolean
  onInsert: (block: string) => void
}

export function LyricsDraftPanel({ songId, hasAnalysis, onInsert }: LyricsDraftPanelProps) {
  const [variants, setVariants] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function draftLyrics() {
    setLoading(true)
    setError(null)
    try {
      const result = await aiApi.draftLyrics(songId)
      setVariants(result.variants)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось придумать песню')
    } finally {
      setLoading(false)
    }
  }

  function insertVariant(variant: string) {
    onInsert(variant.trim())
    setVariants([])
  }

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Придумать песню по анализу и пресету</CardTitle>
        <CardDescription>
          AI соберёт песню из анализа идеи и выбранного пресета. Вставляется только выбранный вариант
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {!hasAnalysis && <p className="text-sm text-muted-foreground">Сначала проанализируйте идею справа</p>}
          <Button size="sm" disabled={loading || !hasAnalysis} onClick={draftLyrics}>
            {loading ? 'Придумываю...' : 'Придумать песню'}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {variants.map((variant, index) => (
          <div key={`draft-${index}`} className="flex flex-col gap-2 rounded-lg border p-3 text-sm">
            <p className="whitespace-pre-wrap font-mono">{variant}</p>
            <div>
              <Button size="sm" onClick={() => insertVariant(variant)}>
                Вставить в конец текста
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
