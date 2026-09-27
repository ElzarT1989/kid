import type {
  ChannelSource,
  ChildProfile,
  ChildStats,
  IngestRunResult,
  Platform,
  SystemStatus,
  VideoSummary,
  WatchHistoryItem,
} from '../types'

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'kidsedu_parent_token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch {
    /* приватный режим/заблокированное хранилище — сессия просто не переживёт перезагрузку */
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    /* см. выше */
  }
}

export class UnauthorizedError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (response.status === 401) {
    clearToken()
    throw new UnauthorizedError('Требуется повторный вход')
  }
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export async function login(password: string): Promise<void> {
  const result = await request<{ token: string }>('/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
  setToken(result.token)
}

export function getChildren(): Promise<ChildProfile[]> {
  return request<ChildProfile[]>('/admin/children')
}

export function createChild(payload: {
  name: string
  age: number
  daily_limit_minutes: number
}): Promise<ChildProfile> {
  return request<ChildProfile>('/admin/children', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateChild(
  childId: number,
  payload: Partial<{ name: string; age: number; daily_limit_minutes: number }>,
): Promise<ChildProfile> {
  return request<ChildProfile>(`/admin/children/${childId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteChild(childId: number): Promise<void> {
  return request<void>(`/admin/children/${childId}`, { method: 'DELETE' })
}

export function getChildStats(childId: number, days = 7): Promise<ChildStats> {
  return request<ChildStats>(`/admin/children/${childId}/stats?days=${days}`)
}

export function getWatchHistory(childId: number, limit = 20): Promise<WatchHistoryItem[]> {
  return request<WatchHistoryItem[]>(`/admin/children/${childId}/watch-history?limit=${limit}`)
}

export function getChannels(activeOnly = false): Promise<ChannelSource[]> {
  return request<ChannelSource[]>(`/admin/channels?active_only=${activeOnly}`)
}

export function createChannel(payload: {
  platform: Platform
  external_id: string
  channel_name?: string
  target_age_group?: number
}): Promise<ChannelSource> {
  return request<ChannelSource>('/admin/channels', { method: 'POST', body: JSON.stringify(payload) })
}

export function deactivateChannel(channelId: number): Promise<void> {
  return request<void>(`/admin/channels/${channelId}`, { method: 'DELETE' })
}

export function getVideos(filters?: { isApproved?: boolean; ageGroup?: number }): Promise<VideoSummary[]> {
  const params = new URLSearchParams()
  if (filters?.isApproved !== undefined) params.set('is_approved', String(filters.isApproved))
  if (filters?.ageGroup !== undefined) params.set('age_group', String(filters.ageGroup))
  const query = params.toString()
  return request<VideoSummary[]>(`/admin/videos${query ? `?${query}` : ''}`)
}

export function moderateVideo(
  videoId: number,
  payload: { is_approved: boolean; rejection_reason?: string | null },
): Promise<VideoSummary> {
  return request<VideoSummary>(`/admin/videos/${videoId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>('/admin/system-status')
}

export function runIngestion(): Promise<IngestRunResult> {
  return request<IngestRunResult>('/admin/ingest/run', { method: 'POST' })
}
