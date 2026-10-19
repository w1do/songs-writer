import { useEffect, useState } from 'react'
import { ChevronRight, LogOut, Music2, SlidersHorizontal, type LucideIcon } from 'lucide-react'
import { ApiError, authApi, presetsApi, setUnauthorizedHandler, songsApi } from '@/api'
import { LoginForm } from '@/components/LoginForm'
import { PresetManager } from '@/components/PresetManager'
import { SongList } from '@/components/SongList'
import { SongWorkspace } from '@/components/SongWorkspace'
import { Button } from '@/components/ui/button'
import type { Preset, Song } from '@/types'

type SessionState = 'checking' | 'anonymous' | 'authenticated' | 'error'
type View = 'songs' | 'song' | 'presets'

interface Route {
  view: View
  songId: string | null
}

function parseHash(hash: string): Route {
  const path = hash.replace(/^#/, '')
  const songMatch = /^\/songs\/([^/]+)$/.exec(path)
  if (songMatch) {
    return { view: 'song', songId: songMatch[1] }
  }
  if (path === '/presets') {
    return { view: 'presets', songId: null }
  }
  return { view: 'songs', songId: null }
}

function navigate(hash: string) {
  window.location.hash = hash
}

function App() {
  const [session, setSession] = useState<SessionState>('checking')
  const [presets, setPresets] = useState<Preset[]>([])
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))
  const [song, setSong] = useState<Song | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const { view, songId } = route

  async function loadPresets() {
    try {
      setPresets(await presetsApi.list())
      setSession('authenticated')
    } catch (err) {
      setSession(err instanceof ApiError && err.status === 401 ? 'anonymous' : 'error')
    }
  }

  useEffect(() => {
    let active = true
    presetsApi.list().then(
      (list) => {
        if (active) {
          setPresets(list)
          setSession('authenticated')
        }
      },
      (err: unknown) => {
        if (active) {
          setSession(err instanceof ApiError && err.status === 401 ? 'anonymous' : 'error')
        }
      }
    )
    return () => {
      active = false
    }
  }, [])

  async function refreshPresets() {
    setPresets(await presetsApi.list())
  }

  useEffect(() => {
    function handleHashChange() {
      setRoute(parseHash(window.location.hash))
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => setSession('anonymous'))
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    if (session !== 'authenticated' || view !== 'song' || !songId) {
      return
    }
    let active = true
    songsApi.get(songId).then(
      (loaded) => {
        if (active) {
          setSong(loaded)
          setNotice(null)
        }
      },
      (err: unknown) => {
        if (active) {
          setNotice(err instanceof ApiError && err.status === 404 ? 'Песня не найдена' : 'Не удалось загрузить песню')
          navigate('#/songs')
        }
      }
    )
    return () => {
      active = false
    }
  }, [session, view, songId])

  async function handleLogout() {
    await authApi.logout().catch(() => undefined)
    setSong(null)
    setPresets([])
    setSession('anonymous')
  }

  if (session !== 'authenticated') {
    return (
      <main className="flex min-h-svh items-center justify-center p-6">
        {session === 'checking' && <p className="text-sm text-muted-foreground">Проверка сессии...</p>}
        {session === 'anonymous' && <LoginForm onLogin={loadPresets} />}
        {session === 'error' && (
          <div className="flex flex-col items-center gap-3 text-sm">
            <p>Не удалось связаться с сервером.</p>
            <Button
              variant="outline"
              onClick={() => {
                setSession('checking')
                loadPresets()
              }}
            >
              Повторить
            </Button>
          </div>
        )}
      </main>
    )
  }

  const navItems: { label: string; hash: string; active: boolean; icon: LucideIcon }[] = [
    { label: 'Песни', hash: '#/songs', active: view === 'songs' || view === 'song', icon: Music2 },
    { label: 'Пресеты', hash: '#/presets', active: view === 'presets', icon: SlidersHorizontal },
  ]

  const crumbs: { label: string; hash?: string }[] = [{ label: 'Главная', hash: '#/songs' }]
  if (view === 'songs') {
    crumbs.push({ label: 'Песни' })
  } else if (view === 'presets') {
    crumbs.push({ label: 'Пресеты' })
  } else {
    crumbs.push({ label: 'Песни', hash: '#/songs' }, { label: song?.title || 'Песня' })
  }

  return (
    <div className="flex min-h-svh w-full flex-col">
      <header className="sticky top-0 z-10 border-b bg-card/95 backdrop-blur">
        <div className="flex w-full items-center justify-between gap-4 px-4 py-3 md:px-8">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex shrink-0 items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Music2 className="size-4" />
              </span>
              <span className="text-base font-semibold">AI Song Builder</span>
            </div>
            <nav className="flex gap-1">
              {navItems.map((item) => (
                <Button
                  key={item.hash}
                  variant={item.active ? 'secondary' : 'ghost'}
                  size="sm"
                  className="gap-2"
                  onClick={() => navigate(item.hash)}
                >
                  <item.icon className="size-4" />
                  {item.label}
                </Button>
              ))}
            </nav>
          </div>
          <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground" onClick={handleLogout}>
            <LogOut className="size-4" />
            Выйти
          </Button>
        </div>
        <div className="border-t px-4 py-2 md:px-8">
          <nav aria-label="Навигация" className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
            {crumbs.map((crumb, index) => (
              <span key={`${crumb.label}-${index}`} className="flex items-center gap-1">
                {index > 0 && <ChevronRight className="size-3.5" />}
                {crumb.hash && index < crumbs.length - 1 ? (
                  <a href={crumb.hash} className="hover:text-foreground hover:underline">
                    {crumb.label}
                  </a>
                ) : (
                  <span className="font-medium text-foreground">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex w-full flex-1 flex-col gap-6 p-4 md:p-8">
        {notice && (
          <div role="alert" className="flex items-center justify-between gap-4 text-sm text-destructive">
            <p>{notice}</p>
            <Button variant="ghost" size="sm" onClick={() => setNotice(null)}>
              Закрыть
            </Button>
          </div>
        )}
        {view === 'songs' && <SongList presets={presets} />}
        {view === 'song' &&
          (song && song.id === songId ? (
            <SongWorkspace key={song.id} song={song} presets={presets} />
          ) : (
            <p className="text-sm text-muted-foreground">Загрузка песни...</p>
          ))}
        {view === 'presets' && <PresetManager presets={presets} onChange={refreshPresets} />}
      </main>
    </div>
  )
}

export default App
