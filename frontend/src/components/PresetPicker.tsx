import { useEffect, useState } from 'react'
import { ApiError, presetsApi } from '@/api'
import { Select } from '@/components/ui/select'
import type { Preset } from '@/types'

interface PresetPickerProps {
  value: string
  onChange: (presetId: string) => void
}

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Не удалось загрузить пресеты.'
}

export function PresetPicker({ value, onChange }: PresetPickerProps) {
  const [presets, setPresets] = useState<Preset[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    presetsApi.list().then(
      (list) => {
        if (active) {
          setPresets(list)
        }
      },
      (err: unknown) => {
        if (active) {
          setError(errorMessage(err))
        }
      }
    )
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="flex flex-col gap-3 rounded-md border p-3">
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Пресет
        <Select value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">Без пресета</option>
          {presets.map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.name}
            </option>
          ))}
        </Select>
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
