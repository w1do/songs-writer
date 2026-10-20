import { songsApi } from '@/api'
import { useState } from 'react'
import { ExportDialog } from '@/components/ExportDialog'
import { SongChat } from '@/components/SongChat'
import { type CopyItem, SongCopyButtons } from '@/components/SongCopyButtons'
import { ReferenceUpload } from '@/components/ReferenceUpload'
import { StoryPanel } from '@/components/StoryPanel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { parseLyricsSections, sectionKey } from '@/lib/lyrics'
import type { Preset, Song } from '@/types'

interface SongWorkspaceProps {
  song: Song
  presets: Preset[]
}

const COPY_LIMIT = 1000

function buildStyleText(preset: Preset | null, song: Song): string {
  if (!preset) {
    return song.track_settings?.style_prompt ?? ''
  }
  const bpm =
    preset.bpm_min != null && preset.bpm_max != null
      ? `${preset.bpm_min}-${preset.bpm_max}`
      : String(preset.bpm_min ?? preset.bpm_max ?? '')
  const parts: [string, string | null | undefined][] = [
    ['Genre', preset.genre],
    ['BPM', bpm],
    ['Energy', preset.energy == null ? '' : String(preset.energy)],
    ['Style', preset.style_prompt],
    ['Sound scene', preset.sound_scene],
    ['Hooks', preset.hooks_prompt],
    ['Effects', preset.effects_prompt],
    ['Chorus vocal style', preset.chorus_vocal_style],
    ['Description', preset.description],
  ]
  return parts
    .filter(([, value]) => value && value.trim())
    .map(([label, value]) => `${label}: ${value}`)
    .join('\n')
    .slice(0, COPY_LIMIT)
}

export function SongWorkspace({ song, presets }: SongWorkspaceProps) {
  const [story, setStory] = useState(song.story)
  const [lyrics, setLyrics] = useState(song.lyrics ?? '')
  const [changedKeys, setChangedKeys] = useState<Set<string>>(() => new Set())
  const [exportOpen, setExportOpen] = useState(false)

  const [presetId, setPresetId] = useState(song.preset_id ?? '')
  const preset = presets.find((item) => item.id === presetId) ?? null

  async function handlePresetChange(next: string) {
    const previous = presetId
    setPresetId(next)
    try {
      await songsApi.update(song.id, { preset_id: next || null })
    } catch {
      setPresetId(previous)
    }
  }
  const sections = parseLyricsSections(lyrics)
  const hasLyrics = lyrics.trim().length > 0

  const copyItems: CopyItem[] = [
    { label: 'Копировать текст песни', value: lyrics },
    { label: 'Копировать style-подсказку', value: buildStyleText(preset, song).slice(0, COPY_LIMIT) },
    {
      label: 'Копировать negative-подсказку',
      value: (
        preset?.negative_style_prompt || song.track_settings?.negative_style_prompt || ''
      ).slice(0, COPY_LIMIT),
    },
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

      <Card>
        <CardHeader>
          <CardTitle>Референс песни</CardTitle>
          <CardDescription>
            Загрузите песню, которая нравится: ИИ определит мотив, подачу и стиль и создаст пресет.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ReferenceUpload />
        </CardContent>
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

      <SongChat
        songId={song.id}
        presetId={presetId}
        onPresetChange={(id) => void handlePresetChange(id)}
        onLyricsChange={handleLyricsChange}
      />

      {exportOpen && <ExportDialog songId={song.id} onClose={() => setExportOpen(false)} />}
    </div>
  )
}
