export interface ChildProfile {
  id: number
  name: string
  age: number
  daily_limit_minutes: number
  avatar_url: string | null
  created_at: string
}

export interface CurrentTopic {
  month: number
  week: number
  topic: string
  status: string
}

export interface DailyStat {
  stat_date: string
  watched_minutes: number
  quiz_accuracy: number | null
}

export interface ChildStats {
  child_id: number
  daily_limit_minutes: number
  today_watched_minutes: number
  today_remaining_minutes: number
  week_watched_minutes: number
  week_quiz_accuracy: number | null
  current_topic: CurrentTopic | null
  daily_breakdown: DailyStat[]
}

export interface WatchHistoryItem {
  id: number
  video_id: number
  video_title: string
  watched_seconds: number
  completed: boolean
  skipped: boolean
  quiz_passed: boolean
  attempts_count: number
  timestamp: string
}

export type Platform = 'youtube' | 'vk'

export interface ChannelSource {
  id: number
  platform: Platform
  external_id: string
  channel_name: string | null
  target_age_group: number | null
  is_active: boolean
  added_by: string | null
  created_at: string
}

export interface VideoSummary {
  id: number
  title: string
  source_platform: Platform
  age_group: number
  is_approved: boolean
  rejection_reason: string | null
  educational_score: number
  topic_tags: string[]
  duration_sec: number
  channel_name: string | null
}
