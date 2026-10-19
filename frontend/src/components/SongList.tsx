import { useEffect, useState } from 'react'
import { Eye, Music2, Plus, Trash2 } from 'lucide-react'
import { songsApi } from '@/api'
import { SongCreateForm } from '@/components/SongCreateForm'
import { Button } from '@/components/ui/button'
import type { Preset, SongListItem } from '@/types'

interface SongListProps {
  presets: Preset[]
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' })
}

function openSong(song: SongListItem) {
  window.location.hash = `#/songs/${song.id}`
}

export function SongList({ presets }: SongListProps) {
  const [songs, setSongs] = useState<SongListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    songsApi.list().then(
      (list) => {
        if (active) {
          setSongs(list)
          setLoading(false)
        }
      },
      (err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить песни')
          setLoading(false)
        }
      }
    )
    return () => {
      active = false
    }
  }, [reloadKey])

  async function handleDelete(song: SongListItem) {
    if (!window.confirm(`Удалить песню «${song.title || 'Без названия'}»?`)) {
      return
    }
    setError(null)
    try {
      await songsApi.remove(song.id)
      setSongs((current) => current.filter((item) => item.id !== song.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить песню')
    }
  }

  function retry() {
    setLoading(true)
    setError(null)
    setReloadKey((key) => key + 1)
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold">Песни</h2>
        <Button variant="outline" className="gap-2" onClick={() => setCreating((value) => !value)}>
          <Plus className="size-4" />
          {creating ? 'Скрыть форму' : 'Новая песня'}
        </Button>
      </div>
      {creating && <SongCreateForm presets={presets} onCreated={() => setCreating(false)} />}
      {loading && <p className="text-sm text-muted-foreground">Загрузка песен...</p>}
      {!loading && error && (
        <div className="flex flex-col items-start gap-3 text-sm">
          <p role="alert" className="text-destructive">
            {error}
          </p>
          <Button variant="outline" onClick={retry}>
            Повторить
          </Button>
        </div>
      )}
      {!loading && !error && songs.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed p-8 text-center">
          <img
            src="https://n8n.w1do.ru/webhook/assets-file?object_key=assets%2Fillustrations%2Ftech%2FSVG%2FAi%20assistant%20talk%20bot%20robot%20assistant.svg"
            alt=""
            className="h-32 w-32 opacity-80"
          />
          <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Music2 className="size-6" />
          </span>
          <p className="text-sm text-muted-foreground">Песен пока нет. Создайте первую песню.</p>
        </div>
      )}
      {!loading && !error && songs.length > 0 && (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {songs.map((song) => (
            <li
              key={song.id}
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:bg-muted/50"
            >
              <div className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Music2 className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{song.title || 'Без названия'}</p>
                  <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">{song.idea}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Обновлено: {formatDate(song.updated_at)}</p>
              <div className="mt-auto flex items-center justify-between gap-2 border-t pt-3">
                <Button variant="secondary" size="sm" className="gap-2" onClick={() => openSong(song)}>
                  <Eye className="size-4" />
                  Открыть
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Удалить песню"
                  title="Удалить песню"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDelete(song)}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
