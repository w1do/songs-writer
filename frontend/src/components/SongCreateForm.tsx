import { useState, type FormEvent } from 'react'
import { songsApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { Preset, Song } from '@/types'

interface SongCreateFormProps {
  presets: Preset[]
  onCreated: (song: Song) => void
}

export function SongCreateForm({ presets, onCreated }: SongCreateFormProps) {
  const [idea, setIdea] = useState('')
  const [title, setTitle] = useState('')
  const [presetId, setPresetId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedIdea = idea.trim()
    if (!trimmedIdea) {
      return
    }
    setPending(true)
    setError(null)
    try {
      const song = await songsApi.create({
        idea: trimmedIdea,
        title: title.trim() || null,
        preset_id: presetId || null,
      })
      window.location.hash = `#/songs/${song.id}`
      onCreated(song)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать песню')
      setPending(false)
    }
  }

  return (
    <Card className="mx-auto w-full max-w-xl">
      <CardHeader>
        <CardTitle>Новая песня</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Идея песни
            <Textarea
              required
              rows={4}
              placeholder="О чём будет песня"
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Название (необязательно)
            <Input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Пресет жанра
            <Select value={presetId} onChange={(event) => setPresetId(event.target.value)}>
              <option value="">Без пресета</option>
              {presets.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.name} · {preset.genre}
                </option>
              ))}
            </Select>
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" disabled={pending || !idea.trim()}>
            {pending ? 'Создание...' : 'Создать песню'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
