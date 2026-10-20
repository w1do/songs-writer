export interface LyricsSection {
  label: string | null
  body: string
}

const SECTION_TAG = /^\s*\[([^\]\n]+)\]\s*$/

export function parseLyricsSections(lyrics: string): LyricsSection[] {
  const sections: LyricsSection[] = []
  let label: string | null = null
  let lines: string[] = []

  function flush() {
    const body = lines.join('\n').trim()
    if (label !== null || body) {
      sections.push({ label, body })
    }
  }

  for (const line of lyrics.split('\n')) {
    const match = SECTION_TAG.exec(line)
    if (match) {
      flush()
      label = match[1].trim()
      lines = []
    } else {
      lines.push(line)
    }
  }
  flush()
  return sections
}

export function sectionKey(section: LyricsSection): string {
  return `${section.label ?? ''}\n${section.body}`
}
