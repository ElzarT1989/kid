export interface ChildProfile {
  id: number
  name: string
  age: number
  daily_limit_minutes: number
  avatar_url: string | null
  created_at: string
}

export interface PlaylistVideo {
  order_index: number
  video_id: number
  title: string
  duration_sec: number
  video_url: string | null
}

export interface TodayPlaylist {
  child_id: number
  playlist_date: string
  status: string
  items: PlaylistVideo[]
}

export interface QuizOption {
  label: string
  emoji: string
}

export interface Quiz {
  id: number
  question_text: string
  audio_url: string | null
  options: QuizOption[]
  correct_option_index: number
}

export interface WatchLogPayload {
  video_id: number
  watched_seconds: number
  completed: boolean
  skipped: boolean
  quiz_passed: boolean
  attempts_count: number
}
