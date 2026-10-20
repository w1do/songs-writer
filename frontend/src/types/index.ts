export type UUID = string

export interface Preset {
  id: UUID
  name: string
  genre: string
  bpm_min: number | null
  bpm_max: number | null
  energy: number | null
  style_prompt: string | null
  negative_style_prompt: string | null
  sound_scene: string | null
  hooks_prompt: string | null
  effects_prompt: string | null
  chorus_vocal_style: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface PresetInput {
  name: string
  genre: string
  bpm_min?: number | null
  bpm_max?: number | null
  energy?: number | null
  style_prompt?: string | null
  negative_style_prompt?: string | null
  sound_scene?: string | null
  hooks_prompt?: string | null
  effects_prompt?: string | null
  chorus_vocal_style?: string | null
  description?: string | null
}

export interface TrackSettings {
  style_prompt?: string | null
  negative_style_prompt?: string | null
  performance?: string | null
}

export type GenerationSettings = Record<string, unknown>

export interface Song {
  id: UUID
  title: string | null
  story: string | null
  idea: string | null
  lyrics: string | null
  track_settings: TrackSettings | null
  analysis: Record<string, unknown> | null
  generation_settings: GenerationSettings | null
  preset_id: UUID | null
  kind: string
  analysis_status: ReferenceAnalysisStatus | null
  created_at: string
  updated_at: string
}

export interface SongListItem {
  id: UUID
  title: string | null
  idea: string
  preset_id: UUID | null
  created_at: string
  updated_at: string
}

export interface SongCreateInput {
  idea: string
  title?: string | null
  preset_id?: UUID | null
}

export interface SongUpdateInput {
  title?: string | null
  idea?: string | null
  story?: string | null
  lyrics?: string | null
  track_settings?: TrackSettings | null
  analysis?: Record<string, unknown> | null
  generation_settings?: GenerationSettings | null
  preset_id?: UUID | null
}

export interface SongExport {
  song_id: UUID
  title: string | null
  lyrics: string | null
  style_prompt: string | null
  negative_style_prompt: string | null
  performance: string | null
  generation_settings: GenerationSettings | null
}

export interface ChatMessage {
  id: UUID
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface SongChatResponse {
  reply: string
  lyrics: string | null
  messages: ChatMessage[]
}

export type ReferenceAnalysisStatus = 'pending' | 'done' | 'failed'

export interface SongReference {
  id: UUID
  title: string | null
  kind: string
  analysis_status: ReferenceAnalysisStatus | null
}

export interface LyricsDraftInput {
  preset_id: UUID | null
}

export interface LyricsDraftResult {
  variants: string[]
}
