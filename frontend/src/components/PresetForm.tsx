import { useState, type FormEvent } from 'react'
import { ApiError, presetsApi } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { Preset, PresetInput } from '@/types'

type TextFieldKey =
  | 'style_prompt'
  | 'negative_style_prompt'
  | 'sound_scene'
  | 'hooks_prompt'
  | 'effects_prompt'
  | 'chorus_vocal_style'
  | 'description'

const TEXT_FIELDS: { key: TextFieldKey; label: string; hint: string }[] = [
  { key: 'style_prompt', label: 'Style-подсказка', hint: 'Описание звучания для генератора музыки: инструменты, атмосфера.' },
  { key: 'negative_style_prompt', label: 'Negative-подсказка', hint: 'Чего избегать в звучании, например «no vocals distortion».' },
  { key: 'sound_scene', label: 'Звуковая сцена', hint: 'Место или обстановка звука, например «ночной город».' },
  { key: 'hooks_prompt', label: 'Подсказка для хуков', hint: 'Каким должен быть короткий цепляющий хук.' },
  { key: 'effects_prompt', label: 'Эффекты', hint: 'Эффекты и обработка голоса или инструментов, например reverb.' },
  { key: 'chorus_vocal_style', label: 'Вокальный стиль припева', hint: 'Как звучит вокал в припеве: гармонии, дабл, выкрики.' },
  { key: 'description', label: 'Описание', hint: 'Короткая заметка для себя, для чего этот пресет.' },
]

interface FormValues {
  name: string
  genre: string
  bpm_min: string
  bpm_max: string
  energy: string
  style_prompt: string
  negative_style_prompt: string
  sound_scene: string
  hooks_prompt: string
  effects_prompt: string
  chorus_vocal_style: string
  description: string
}

interface PresetFormProps {
  preset: Preset | null
  onSaved: () => Promise<void>
  onCancel: () => void
}

function toFormValues(preset: Preset | null): FormValues {
  return {
    name: preset?.name ?? '',
    genre: preset?.genre ?? '',
    bpm_min: preset?.bpm_min?.toString() ?? '',
    bpm_max: preset?.bpm_max?.toString() ?? '',
    energy: preset?.energy?.toString() ?? '',
    style_prompt: preset?.style_prompt ?? '',
    negative_style_prompt: preset?.negative_style_prompt ?? '',
    sound_scene: preset?.sound_scene ?? '',
    hooks_prompt: preset?.hooks_prompt ?? '',
    effects_prompt: preset?.effects_prompt ?? '',
    chorus_vocal_style: preset?.chorus_vocal_style ?? '',
    description: preset?.description ?? '',
  }
}

function parseOptionalNumber(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

function optionalText(value: string): string | null {
  return value.trim() || null
}

function toPresetInput(values: FormValues): PresetInput {
  return {
    name: values.name.trim(),
    genre: values.genre.trim(),
    bpm_min: parseOptionalNumber(values.bpm_min),
    bpm_max: parseOptionalNumber(values.bpm_max),
    energy: parseOptionalNumber(values.energy),
    style_prompt: optionalText(values.style_prompt),
    negative_style_prompt: optionalText(values.negative_style_prompt),
    sound_scene: optionalText(values.sound_scene),
    hooks_prompt: optionalText(values.hooks_prompt),
    effects_prompt: optionalText(values.effects_prompt),
    chorus_vocal_style: optionalText(values.chorus_vocal_style),
    description: optionalText(values.description),
  }
}

function formatError(err: unknown): string {
  if (err instanceof ApiError && err.status === 422) {
    return `Ошибка валидации: ${err.message}`
  }
  return err instanceof Error ? err.message : 'Не удалось сохранить пресет'
}

export function PresetForm({ preset, onSaved, onCancel }: PresetFormProps) {
  const [values, setValues] = useState<FormValues>(() => toFormValues(preset))
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  function updateField(key: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      const input = toPresetInput(values)
      if (preset) {
        await presetsApi.update(preset.id, input)
      } else {
        await presetsApi.create(input)
      }
      await onSaved()
    } catch (err) {
      setError(formatError(err))
      setPending(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{preset ? 'Редактирование пресета' : 'Новый пресет'}</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Название
            <Input
              required
              maxLength={200}
              value={values.name}
              onChange={(event) => updateField('name', event.target.value)}
            />
            <span className="font-normal text-xs text-muted-foreground">Имя пресета в списках, например «Underground rap».</span>
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Жанр
            <Input
              required
              maxLength={100}
              value={values.genre}
              onChange={(event) => updateField('genre', event.target.value)}
            />
            <span className="font-normal text-xs text-muted-foreground">Основной жанр, например underground или rap.</span>
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              BPM min
              <Input
                type="number"
                step={1}
                value={values.bpm_min}
                onChange={(event) => updateField('bpm_min', event.target.value)}
              />
              <span className="font-normal text-xs text-muted-foreground">Нижняя граница темпа.</span>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              BPM max
              <Input
                type="number"
                step={1}
                value={values.bpm_max}
                onChange={(event) => updateField('bpm_max', event.target.value)}
              />
              <span className="font-normal text-xs text-muted-foreground">Верхняя граница, не меньше min.</span>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              Энергия
              <Input
                type="number"
                step="any"
                value={values.energy}
                onChange={(event) => updateField('energy', event.target.value)}
              />
              <span className="font-normal text-xs text-muted-foreground">От 0 (тихо) до 1 (драйвово).</span>
            </label>
          </div>
          {TEXT_FIELDS.map((field) => (
            <label key={field.key} className="flex flex-col gap-1.5 text-sm font-medium">
              {field.label}
              <Textarea
                rows={2}
                value={values[field.key]}
                onChange={(event) => updateField(field.key, event.target.value)}
              />
              <span className="font-normal text-xs text-muted-foreground">{field.hint}</span>
            </label>
          ))}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={pending}>
              {pending ? 'Сохранение...' : 'Сохранить'}
            </Button>
            <Button type="button" variant="ghost" disabled={pending} onClick={onCancel}>
              Отмена
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
