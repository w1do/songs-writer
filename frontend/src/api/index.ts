import { request } from './client'
import type {
  ChorusResult,
  FinishSongResult,
  HookResult,
  LineActionRequest,
  LineActionResult,
  Preset,
  PresetInput,
  Song,
  SongCreateInput,
  SongExport,
  SongListItem,
  SongUpdateInput,
  StructureResult,
} from '@/types'

export { ApiError, setUnauthorizedHandler } from './client'

export const authApi = {
  login: (email: string, password: string) => request<void>('POST', '/auth/login', { email, password }),
  logout: () => request<void>('POST', '/auth/logout'),
}

export const presetsApi = {
  list: () => request<Preset[]>('GET', '/presets'),
  get: (id: string) => request<Preset>('GET', `/presets/${id}`),
  create: (body: PresetInput) => request<Preset>('POST', '/presets', body),
  update: (id: string, body: Partial<PresetInput>) => request<Preset>('PATCH', `/presets/${id}`, body),
  remove: (id: string) => request<void>('DELETE', `/presets/${id}`),
  generate: (prompt: string) => request<Preset>('POST', '/presets/generate', { prompt }),
}

export const songsApi = {
  list: () => request<SongListItem[]>('GET', '/songs'),
  create: (body: SongCreateInput) => request<Song>('POST', '/songs', body),
  remove: (id: string) => request<void>('DELETE', `/songs/${id}`),
  get: (id: string) => request<Song>('GET', `/songs/${id}`),
  update: (id: string, body: SongUpdateInput) => request<Song>('PATCH', `/songs/${id}`, body),
  exportData: (id: string) => request<SongExport>('GET', `/songs/${id}/export`),
}

export const aiApi = {
  analyzeIdea: (songId: string) => request<Song>('POST', `/songs/${songId}/analyze-idea`),
  lineAction: (songId: string, body: LineActionRequest) =>
    request<LineActionResult>('POST', `/songs/${songId}/line-action`, body),
  continueSection: (songId: string, section: string) =>
    request<LineActionResult>('POST', `/songs/${songId}/continue-section`, { section }),
  createHook: (songId: string) => request<HookResult>('POST', `/songs/${songId}/create-hook`),
  createChorus: (songId: string) => request<ChorusResult>('POST', `/songs/${songId}/create-chorus`),
  structureSuggestion: (songId: string) =>
    request<StructureResult>('POST', `/songs/${songId}/structure-suggestion`),
  finishSong: (songId: string) => request<FinishSongResult>('POST', `/songs/${songId}/finish-song`),
  prepareTrack: (songId: string) => request<Song>('POST', `/songs/${songId}/prepare-track`),
}
