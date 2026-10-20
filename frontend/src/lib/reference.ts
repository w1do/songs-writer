export const REFERENCE_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac']

export const REFERENCE_MAX_BYTES = 20 * 1024 * 1024

export function validateReferenceFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!REFERENCE_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return 'Поддерживаются форматы: MP3, WAV, M4A, FLAC'
  }
  if (file.size > REFERENCE_MAX_BYTES) {
    return 'Файл больше 20 МБ'
  }
  return null
}
