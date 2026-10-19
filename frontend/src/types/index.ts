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

export interface AnalysisResult {
  theme: string
  emotion: string
  genre: string
  bpm: number
  energy: number
  structure: string[]
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
  idea: string | null
  lyrics: string | null
  track_settings: TrackSettings | null
  analysis: AnalysisResult | Record<string, unknown> | null
  generation_settings: GenerationSettings | null
  preset_id: UUID | null
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

export type LineActionType = 'variants' | 'continue' | 'rewrite' | 'rhyme' | 'flow' | 'vocal'

export interface LineActionRequest {
  action: LineActionType
  line: string
  selection?: string | null
}

export interface LineActionResult {
  variants: string[]
  note: string | null
}

export interface HookResult {
  variants: string[]
}

export interface ChorusResult {
  variants: string[][]
}

export interface LyricsDraftResult {
  variants: string[]
}

export interface StructureResult {
  sections: string[]
  reason: string | null
}

export interface FinishSongResult {
  comments: string[]
}
