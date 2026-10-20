import { useState, type ChangeEvent } from 'react'
import { ApiError, referencesApi } from '@/api'
import { ReferenceStatus } from '@/components/ReferenceStatus'
import { Input } from '@/components/ui/input'
import { REFERENCE_EXTENSIONS, validateReferenceFile } from '@/lib/reference'

interface ReferenceUploadProps {
  onDone?: () => void
}

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Не удалось загрузить референс. Попробуйте ещё раз.'
}

export function ReferenceUpload({ onDone }: ReferenceUploadProps) {
  const [songId, setSongId] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }
    const problem = validateReferenceFile(file)
    if (problem) {
      setError(problem)
      return
    }
    setPending(true)
    setError(null)
    try {
      const reference = await referencesApi.upload(file)
      setSongId(reference.id)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Загрузить референс песни
        <Input
          type="file"
          accept={REFERENCE_EXTENSIONS.join(',')}
          disabled={pending}
          onChange={handleFileChange}
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {songId && <ReferenceStatus key={songId} songId={songId} onDone={onDone ?? (() => {})} />}
    </div>
  )
}
