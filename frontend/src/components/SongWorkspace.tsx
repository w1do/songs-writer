import { useState } from 'react'
import { AnalysisSidebar } from '@/components/AnalysisSidebar'
import { ExportDialog } from '@/components/ExportDialog'
import { FinishSongPanel } from '@/components/FinishSongPanel'
import { HookChorusPanel } from '@/components/HookChorusPanel'
import { LineActionPanel } from '@/components/LineActionPanel'
import { LyricsDraftPanel } from '@/components/LyricsDraftPanel'
import { LyricsEditor, type TextRange } from '@/components/LyricsEditor'
import { PrepareTrackPanel } from '@/components/PrepareTrackPanel'
import { type CopyItem, SongCopyButtons } from '@/components/SongCopyButtons'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAutosave, type AutosaveStatus } from '@/hooks/useAutosave'
import type { Preset, Song, TrackSettings } from '@/types'

interface SongWorkspaceProps {
  song: Song
  presets: Preset[]
}

const WIZARD_STEPS = ['Идея и анализ', 'Текст', 'Hook и Chorus', 'Финал', 'Prepare Track']

const SAVE_STATUS_LABELS: Record<AutosaveStatus, string> = {
  idle: 'нет изменений',
  saving: 'сохранение...',
  saved: 'сохранено',
  error: 'ошибка сохранения',
}

export function SongWorkspace({ song, presets }: SongWorkspaceProps) {
  const [lyrics, setLyrics] = useState(song.lyrics ?? '')
  const [trackSettings, setTrackSettings] = useState<TrackSettings | null>(song.track_settings)
  const [analysis, setAnalysis] = useState(song.analysis as Record<string, unknown> | null)
  const [generationSettings, setGenerationSettings] = useState(song.generation_settings)
  const [range, setRange] = useState<TextRange>({ start: 0, end: 0 })
  const [step, setStep] = useState(0)
  const [exportOpen, setExportOpen] = useState(false)

  const preset = presets.find((item) => item.id === song.preset_id) ?? null
  const hasAnalysis = Boolean(analysis && Object.keys(analysis).length > 0)
  const hasLyrics = lyrics.trim().length > 0
  const stepHint = [
    hasAnalysis
      ? 'Анализ готов: жанр, BPM и структура видны справа. Переходите к тексту.'
      : 'Нажмите «Проанализировать идею» справа, чтобы получить жанр, BPM и структуру.',
    hasLyrics
      ? 'Выделите строку мышью и выберите AI-действие. «Продолжить куплет» работает без выделения. Структура песни показана под редактором.'
      : 'Нажмите «Шаблон песни» над редактором или добавьте раздел кнопкой [VERSE], затем напишите первую строку.',
    'Hook и Chorus добавляются в текст только по нажатию кнопки вставки.',
    'Финальный разбор не меняет текст песни.',
    'Проверьте Style Prompt и Generation Settings, затем экспортируйте данные.',
  ][step]
  const lastStep = WIZARD_STEPS.length - 1
  const stylePrompt = trackSettings?.style_prompt || preset?.style_prompt || ''
  const negativeStylePrompt = trackSettings?.negative_style_prompt || preset?.negative_style_prompt || ''

  const saveStatus = useAutosave(song.id, {
    lyrics,
    track_settings: trackSettings,
    analysis,
    generation_settings: generationSettings,
  })

  const copyItems: CopyItem[] = [
    { label: 'Копировать текст песни', value: lyrics },
    { label: 'Копировать style-подсказку', value: stylePrompt },
    { label: 'Копировать negative-подсказку', value: negativeStylePrompt },
  ]

  function replaceRange(target: TextRange, text: string) {
    setLyrics((current) => current.slice(0, target.start) + text + current.slice(target.end))
  }

  function appendBlock(block: string) {
    setLyrics((current) => (current.trim() ? `${current.trimEnd()}\n\n${block}` : block))
  }

  function applySong(updated: Song) {
    setAnalysis(updated.analysis as Record<string, unknown> | null)
    setTrackSettings(updated.track_settings)
    setGenerationSettings(updated.generation_settings)
  }

  function applyPreparedTrack(updated: Song) {
    setTrackSettings(updated.track_settings)
    setGenerationSettings(updated.generation_settings)
  }

  return (
    <div className="grid w-full gap-6 xl:grid-cols-[minmax(0,1fr)_28rem]">
      <div className="flex min-w-0 flex-col gap-6">
        <ol className="flex flex-wrap items-center gap-2" aria-label="Шаги создания песни">
          {WIZARD_STEPS.map((label, index) => (
            <li key={label}>
              <Button
                variant={step === index ? 'default' : 'outline'}
                size="sm"
                aria-current={step === index ? 'step' : undefined}
                onClick={() => setStep(index)}
              >
                {index + 1}. {label}
              </Button>
            </li>
          ))}
        </ol>
        <Card size="sm">
          <CardHeader>
            <CardTitle>
              Шаг {step + 1} из {WIZARD_STEPS.length}: {WIZARD_STEPS[step]}
            </CardTitle>
            <CardDescription>{stepHint}</CardDescription>
          </CardHeader>
        </Card>
        <div className={step === 0 ? 'flex flex-col gap-6' : 'hidden'}>
          <Card>
            <CardHeader>
              <CardTitle>Ваша идея</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{song.idea || 'не указана'}</p>
            </CardContent>
          </Card>
        </div>
        <div className={step === 1 ? 'flex flex-col gap-6' : 'hidden'}>
          <Card>
            <CardHeader>
              <CardTitle>{song.title || 'Песня без названия'}</CardTitle>
              <CardDescription className={saveStatus === 'error' ? 'text-destructive' : undefined}>
                Автосохранение: {SAVE_STATUS_LABELS[saveStatus]}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <LyricsEditor value={lyrics} onChange={setLyrics} onRangeChange={setRange} />
              <SongCopyButtons items={copyItems} />
            </CardContent>
          </Card>
          <LyricsDraftPanel songId={song.id} hasAnalysis={hasAnalysis} onInsert={appendBlock} />
          <LineActionPanel songId={song.id} lyrics={lyrics} range={range} onReplace={replaceRange} />
        </div>
        <div className={step === 2 ? 'flex flex-col gap-6' : 'hidden'}>
          <HookChorusPanel songId={song.id} onInsert={appendBlock} />
        </div>
        <div className={step === 3 ? 'flex flex-col gap-6' : 'hidden'}>
          <FinishSongPanel songId={song.id} />
        </div>
        <div className={step === 4 ? 'flex flex-col gap-6' : 'hidden'}>
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => setExportOpen(true)}>
              Export
            </Button>
          </div>
          <PrepareTrackPanel
            songId={song.id}
            trackSettings={trackSettings}
            generationSettings={generationSettings}
            onPrepared={applyPreparedTrack}
            onTrackSettingsChange={setTrackSettings}
            onGenerationSettingsChange={setGenerationSettings}
          />
        </div>
        <div className="flex items-center justify-between gap-2">
          <Button variant="outline" disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))}>
            {step > 0 ? `Назад: ${WIZARD_STEPS[step - 1]}` : 'Назад'}
          </Button>
          <Button disabled={step === lastStep} onClick={() => setStep((current) => Math.min(lastStep, current + 1))}>
            {step < lastStep ? `Далее: ${WIZARD_STEPS[step + 1]}` : 'Далее'}
          </Button>
        </div>
      </div>
      <AnalysisSidebar
        songId={song.id}
        analysis={analysis}
        preset={preset}
        onAnalysisChange={setAnalysis}
        onSongUpdate={applySong}
      />
      {exportOpen && <ExportDialog songId={song.id} onClose={() => setExportOpen(false)} />}
    </div>
  )
}
