import { useState } from 'react'
import { ExportDialog } from '@/components/ExportDialog'
import { SongChat } from '@/components/SongChat'
import { type CopyItem, SongCopyButtons } from '@/components/SongCopyButtons'
import { StoryPanel } from '@/components/StoryPanel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { parseLyricsSections, sectionKey } from '@/lib/lyrics'
import type { Preset, Song } from '@/types'

interface SongWorkspaceProps {
  song: Song
  presets: Preset[]
}

export function SongWorkspace({ song, presets }: SongWorkspaceProps) {
  const [story, setStory] = useState(song.story)
  const [lyrics, setLyrics] = useState(song.lyrics ?? '')
  const [changedKeys, setChangedKeys] = useState<Set<string>>(() => new Set())
  const [exportOpen, setExportOpen] = useState(false)

  const preset = presets.find((item) => item.id === song.preset_id) ?? null
  const sections = parseLyricsSections(lyrics)
  const hasLyrics = lyrics.trim().length > 0

  const copyItems: CopyItem[] = [
    { label: 'Копировать текст песни', value: lyrics },
    { label: 'Копировать style-подсказку', value: preset?.style_prompt ?? '' },
    { label: 'Копировать negative-подсказку', value: preset?.negative_style_prompt ?? '' },
  ]

  function handleLyricsChange(next: string) {
    const previous = new Set(parseLyricsSections(lyrics).map(sectionKey))
    setChangedKeys(
      new Set(
        parseLyricsSections(next)
          .map(sectionKey)
          .filter((key) => !previous.has(key))
      )
    )
    setLyrics(next)
  }

  return (
    <div className="grid w-full gap-6">
      <Card size="sm">
        <CardHeader>
          <CardTitle>{song.title || 'Песня без названия'}</CardTitle>
          <CardDescription>Пресет: {preset ? `${preset.name} (${preset.genre})` : 'не выбран'}</CardDescription>
        </CardHeader>
      </Card>

      <StoryPanel songId={song.id} story={story} onSaved={setStory} />

      <Card>
        <CardHeader>
          <CardTitle>Текст песни</CardTitle>
          <CardDescription>Текст создаёт ИИ по истории и вашим просьбам в чате. Редактировать вручную нельзя.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {hasLyrics ? (
            <div className="flex flex-col gap-4">
              {sections.map((section, index) => {
                const key = sectionKey(section)
                return (
                  <section
                    key={`${index}-${key}`}
                    className={
                      changedKeys.has(key)
                        ? 'flex flex-col gap-1 rounded-md bg-primary/10 p-2'
                        : 'flex flex-col gap-1 p-2'
                    }
                  >
                    {section.label && (
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        [{section.label}]
                      </h3>
                    )}
                    <p className="whitespace-pre-wrap text-sm">{section.body}</p>
                  </section>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Расскажите историю и напишите в чат, с чего начать.
            </p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SongCopyButtons items={copyItems} />
            <Button variant="outline" size="sm" onClick={() => setExportOpen(true)}>
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      <SongChat songId={song.id} onLyricsChange={handleLyricsChange} />

      {exportOpen && <ExportDialog songId={song.id} onClose={() => setExportOpen(false)} />}
    </div>
  )
}
