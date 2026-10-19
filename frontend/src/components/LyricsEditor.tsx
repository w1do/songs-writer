import { useRef, type UIEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export interface TextRange {
  start: number
  end: number
}

const SECTION_PATTERN = /(\[[A-Za-z][A-Za-z0-9 -]*\])/

const SECTION_BUTTONS = ['INTRO', 'VERSE', 'PRE-CHORUS', 'CHORUS', 'BRIDGE', 'OUTRO']

const SECTION_HINTS: Record<string, string> = {
  INTRO: 'Вступление: короткое начало песни перед первым куплетом',
  VERSE: 'Куплет: основной рассказ песни, обычно повторяется с новым текстом',
  'PRE-CHORUS': 'Предприпев: переход от куплета к припеву, нарастает напряжение',
  CHORUS: 'Припев: главная запоминающаяся часть, повторяется и несёт основную мысль',
  BRIDGE: 'Бридж: контрастный раздел, даёт новый взгляд перед финалом',
  OUTRO: 'Концовка: финал песни, завершает историю или мысль',
}

const SONG_TEMPLATE = [
  '[INTRO]',
  '',
  '[VERSE]',
  '',
  '[CHORUS]',
  '',
  '[VERSE]',
  '',
  '[CHORUS]',
  '',
  '[BRIDGE]',
  '',
  '[CHORUS]',
  '',
  '[OUTRO]',
  '',
].join('\n')

interface SectionInfo {
  name: string
  start: number
  lines: number
}

function parseSections(value: string): SectionInfo[] {
  const headers = [...value.matchAll(/^\[[^\]\n]+\]\s*$/gm)]
  return headers.map((match, index) => {
    const start = match.index ?? 0
    const bodyStart = start + match[0].length
    const bodyEnd = headers[index + 1]?.index ?? value.length
    const lines = value
      .slice(bodyStart, bodyEnd)
      .split('\n')
      .filter((line) => line.trim().length > 0).length
    return { name: match[0].trim(), start, lines }
  })
}

interface LyricsEditorProps {
  value: string
  onChange: (value: string) => void
  onRangeChange: (range: TextRange) => void
}

export function LyricsEditor({ value, onChange, onRangeChange }: LyricsEditorProps) {
  const mirrorRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const parts = value.split(SECTION_PATTERN)
  const sections = parseSections(value)

  function syncScroll(event: UIEvent<HTMLTextAreaElement>) {
    if (mirrorRef.current) {
      mirrorRef.current.scrollTop = event.currentTarget.scrollTop
    }
  }

  function focusAt(position: number) {
    const element = textareaRef.current
    if (!element) {
      return
    }
    element.focus()
    element.setSelectionRange(position, position)
    onRangeChange({ start: position, end: position })
  }

  function appendSection(name: string) {
    const marker = `[${name}]`
    const next = value.trim() ? `${value.trimEnd()}\n\n${marker}\n` : `${marker}\n`
    onChange(next)
    focusAt(next.length)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Добавить раздел:</span>
        {SECTION_BUTTONS.map((name) => (
          <Button
            key={name}
            variant="outline"
            size="xs"
            title={SECTION_HINTS[name]}
            onClick={() => appendSection(name)}
          >
            [{name}]
          </Button>
        ))}
        {!value.trim() && (
          <Button size="xs" onClick={() => onChange(SONG_TEMPLATE)}>
            Шаблон песни
          </Button>
        )}
      </div>
      <div className="relative rounded-lg border border-input focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
        <div
          ref={mirrorRef}
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 overflow-hidden px-2.5 py-2 font-mono text-sm leading-6 break-words whitespace-pre-wrap"
        >
          {parts.map((part, index) =>
            index % 2 === 1 ? (
              <mark key={index} className="rounded bg-primary/15 font-semibold text-primary">
                {part}
              </mark>
            ) : (
              <span key={index}>{part}</span>
            )
          )}
          {value.endsWith('\n') ? ' ' : null}
        </div>
        <Textarea
          ref={textareaRef}
          aria-label="Текст песни"
          placeholder="Текст песни. Нажмите «Шаблон песни» или добавьте раздел кнопкой выше"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onSelect={(event) =>
            onRangeChange({
              start: event.currentTarget.selectionStart,
              end: event.currentTarget.selectionEnd,
            })
          }
          onScroll={syncScroll}
          className="relative min-h-72 resize-y border-0 bg-transparent px-2.5 py-2 font-mono text-sm leading-6 break-words text-transparent caret-foreground focus-visible:ring-0 whitespace-pre-wrap"
        />
      </div>
      {sections.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium">Структура песни (нажмите, чтобы перейти к разделу):</span>
          <div className="flex flex-wrap gap-2">
            {sections.map((section) => (
              <Button
                key={section.start}
                variant="secondary"
                size="xs"
                onClick={() => focusAt(section.start)}
              >
                {section.name} · строк: {section.lines}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
