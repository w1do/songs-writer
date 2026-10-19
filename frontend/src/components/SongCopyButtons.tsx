import { useState } from 'react'
import { Button } from '@/components/ui/button'

export interface CopyItem {
  label: string
  value: string
}

interface SongCopyButtonsProps {
  items: CopyItem[]
}

export function SongCopyButtons({ items }: SongCopyButtonsProps) {
  const [copied, setCopied] = useState<string | null>(null)

  async function copy(item: CopyItem) {
    try {
      await navigator.clipboard.writeText(item.value)
      setCopied(item.label)
    } catch {
      setCopied(null)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {items.map((item) => (
        <Button key={item.label} variant="outline" size="sm" disabled={!item.value} onClick={() => copy(item)}>
          {item.label}
        </Button>
      ))}
      {copied && <span className="text-xs text-muted-foreground">Скопировано: {copied}</span>}
    </div>
  )
}
