import { useState } from 'react'
import { Pencil, Sliders, Trash2 } from 'lucide-react'
import { presetsApi } from '@/api'
import { PresetForm } from '@/components/PresetForm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Preset } from '@/types'

interface PresetManagerProps {
  presets: Preset[]
  onChange: () => Promise<void>
}

function formatBpm(preset: Preset): string | null {
  if (preset.bpm_min !== null && preset.bpm_max !== null) {
    return `${preset.bpm_min}–${preset.bpm_max} BPM`
  }
  if (preset.bpm_min !== null) {
    return `${preset.bpm_min} BPM`
  }
  if (preset.bpm_max !== null) {
    return `${preset.bpm_max} BPM`
  }
  return null
}

export function PresetManager({ presets, onChange }: PresetManagerProps) {
  const [editing, setEditing] = useState<Preset | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [prompt, setPrompt] = useState('')
  const [generating, setGenerating] = useState(false)

  async function handleGenerate() {
    if (!prompt.trim()) {
      return
    }
    setError(null)
    setGenerating(true)
    try {
      await presetsApi.generate(prompt.trim())
      setPrompt('')
      await onChange()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сгенерировать пресет')
    } finally {
      setGenerating(false)
    }
  }

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(preset: Preset) {
    setEditing(preset)
    setFormOpen(true)
  }

  function closeForm() {
    setEditing(null)
    setFormOpen(false)
  }

  async function handleSaved() {
    await onChange()
    closeForm()
  }

  async function handleDelete(preset: Preset) {
    if (!window.confirm(`Удалить пресет «${preset.name}»?`)) {
      return
    }
    setError(null)
    try {
      await presetsApi.remove(preset.id)
      if (editing?.id === preset.id) {
        closeForm()
      }
      await onChange()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить пресет')
    }
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold">Пресеты</h2>
        <Button variant="outline" onClick={openCreate}>
          Новый пресет
        </Button>
      </div>
      <div className="flex flex-col gap-2 rounded-lg border p-4">
        <p className="text-sm font-medium">Создать пресет по описанию</p>
        <p className="text-xs text-muted-foreground">Например: underground, rap 90 bpm</p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            aria-label="Описание пресета"
            value={prompt}
            disabled={generating}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleGenerate()}
            placeholder="underground, rap 90 bpm"
          />
          <Button onClick={handleGenerate} disabled={generating || !prompt.trim()}>
            {generating ? 'Генерация...' : 'Сгенерировать'}
          </Button>
        </div>
      </div>
      {formOpen && (
        <PresetForm key={editing?.id ?? 'new'} preset={editing} onSaved={handleSaved} onCancel={closeForm} />
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {presets.length === 0 ? (
        <p className="text-sm text-muted-foreground">Пресетов пока нет.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {presets.map((preset) => (
            <li
              key={preset.id}
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:bg-muted/50"
            >
              <div className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Sliders className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{preset.name}</p>
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {[preset.genre, formatBpm(preset)].filter(Boolean).join(' · ')}
                  </p>
                </div>
              </div>
              {preset.description && (
                <p className="line-clamp-3 text-sm text-muted-foreground">{preset.description}</p>
              )}
              <div className="mt-auto flex items-center justify-between gap-2 border-t pt-3">
                <Button variant="outline" size="sm" className="gap-2" onClick={() => openEdit(preset)}>
                  <Pencil className="size-4" />
                  Изменить
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 text-destructive hover:text-destructive"
                  onClick={() => handleDelete(preset)}
                >
                  <Trash2 className="size-4" />
                  Удалить
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
