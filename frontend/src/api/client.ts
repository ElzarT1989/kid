import type { ChildProfile, Quiz, TodayPlaylist, WatchLogPayload } from '../types'

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export function mediaUrl(path: string | null): string | null {
  return path ? `${API_BASE_URL}${path}` : null
}

export function getChildren(): Promise<ChildProfile[]> {
  return request<ChildProfile[]>('/admin/children')
}

export function getChild(childId: number): Promise<ChildProfile> {
  return request<ChildProfile>(`/admin/children/${childId}`)
}

export function getTodayPlaylist(childId: number): Promise<TodayPlaylist> {
  return request<TodayPlaylist>(`/player/${childId}/today`)
}

export function getVideoQuizzes(videoId: number): Promise<Quiz[]> {
  return request<Quiz[]>(`/player/videos/${videoId}/quizzes`)
}

export function postWatchLog(childId: number, payload: WatchLogPayload): Promise<void> {
  return request<void>(`/player/${childId}/watch-log`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
