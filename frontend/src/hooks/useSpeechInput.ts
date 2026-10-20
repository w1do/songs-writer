import { useCallback, useEffect, useRef, useState } from 'react'

interface SpeechRecognitionResultLike {
  readonly isFinal: boolean
  readonly 0: { readonly transcript: string }
}

interface SpeechRecognitionEventLike {
  readonly resultIndex: number
  readonly results: ArrayLike<SpeechRecognitionResultLike>
}

interface SpeechRecognitionErrorEventLike {
  readonly error: string
}

interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

export interface SpeechInput {
  supported: boolean
  listening: boolean
  transcript: string
  error: string | null
  start: () => void
  stop: () => void
}

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Доступ к микрофону запрещён. Пишите текст вручную.',
  'service-not-allowed': 'Распознавание речи недоступно. Пишите текст вручную.',
  'no-speech': 'Речь не распознана. Попробуйте ещё раз.',
  'audio-capture': 'Микрофон не найден. Пишите текст вручную.',
  network: 'Ошибка сети при распознавании речи.',
}

function getRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') {
    return null
  }
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null
}

export function useSpeechInput(onFinal: (text: string) => void): SpeechInput {
  const Recognition = getRecognitionConstructor()
  const supported = Recognition !== null
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const onFinalRef = useRef(onFinal)

  useEffect(() => {
    onFinalRef.current = onFinal
  }, [onFinal])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    recognitionRef.current = null
    setListening(false)
    setTranscript('')
  }, [])

  const start = useCallback(() => {
    const Constructor = getRecognitionConstructor()
    if (!Constructor || recognitionRef.current) {
      return
    }
    setError(null)
    const recognition = new Constructor()
    recognition.lang = 'ru-RU'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event) => {
      let interim = ''
      let final = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        if (result.isFinal) {
          final += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }
      if (final) {
        onFinalRef.current(final.trim())
      }
      setTranscript(interim.trim())
    }
    recognition.onerror = (event) => {
      setError(ERROR_MESSAGES[event.error] ?? 'Не удалось распознать речь.')
      recognitionRef.current = null
      setListening(false)
    }
    recognition.onend = () => {
      recognitionRef.current = null
      setListening(false)
      setTranscript('')
    }
    recognitionRef.current = recognition
    setListening(true)
    recognition.start()
  }, [])

  useEffect(() => () => recognitionRef.current?.abort(), [])

  return { supported, listening, transcript, error, start, stop }
}
