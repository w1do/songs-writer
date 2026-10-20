import { request } from './client'
import type {
  ChatMessage,
  LyricsDraftResult,
  Preset,
  PresetInput,
  Song,
  SongChatResponse,
  SongCreateInput,
  SongExport,
  SongListItem,
  SongReference,
  SongUpdateInput,
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

export const referencesApi = {
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<SongReference>('POST', '/songs/reference', body)
  },
}

export const aiApi = {
  listMessages: (songId: string) => request<ChatMessage[]>('GET', `/songs/${songId}/messages`),
  chat: (songId: string, message: string) =>
    request<SongChatResponse>('POST', `/songs/${songId}/chat`, { message }),
  draftLyrics: (songId: string, presetId: string | null) =>
    request<LyricsDraftResult>('POST', `/songs/${songId}/draft-lyrics`, { preset_id: presetId }),
}
