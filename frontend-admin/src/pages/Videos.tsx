import { useEffect, useState } from 'react'
import { getVideos, moderateVideo } from '../api/client'
import type { VideoSummary } from '../types'

type FilterValue = 'all' | 'approved' | 'rejected'

export default function Videos() {
  const [videos, setVideos] = useState<VideoSummary[]>([])
  const [filter, setFilter] = useState<FilterValue>('all')
  const [loading, setLoading] = useState(true)

  const load = (value: FilterValue) => {
    setLoading(true)
    getVideos(value === 'all' ? undefined : { isApproved: value === 'approved' })
      .then(setVideos)
      .finally(() => setLoading(false))
  }

  useEffect(() => load(filter), [filter])

  const handleToggle = async (video: VideoSummary) => {
    await moderateVideo(video.id, {
      is_approved: !video.is_approved,
      rejection_reason: video.is_approved ? 'Заблокировано родителем через веб-панель' : null,
    })
    load(filter)
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Видео и модерация</h1>

      <div className="flex gap-1">
        {(
          [
            ['all', 'Все'],
            ['approved', 'Одобренные'],
            ['rejected', 'Отклонённые'],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className="rounded-lg px-3 py-1.5 text-sm"
            style={{
              background: filter === value ? 'var(--gridline)' : 'transparent',
              color: 'var(--text-primary)',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Загрузка…</p>
      ) : (
        <div className="flex flex-col gap-2">
          {videos.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>Видео нет.</p>}
          {videos.map((video) => (
            <div
              key={video.id}
              className="rounded-lg border p-3"
              style={{ borderColor: 'var(--gridline)' }}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{video.title}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {video.age_group} лет · {Math.round(video.duration_sec / 60)} мин · оценка{' '}
                    {video.educational_score}/10
                    {video.channel_name && ` · ${video.channel_name}`}
                  </div>
                  {video.topic_tags.length > 0 && (
                    <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {video.topic_tags.join(', ')}
                    </div>
                  )}
                  {!video.is_approved && video.rejection_reason && (
                    <div className="text-xs" style={{ color: 'var(--status-critical)' }}>
                      Причина: {video.rejection_reason}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleToggle(video)}
                  className="whitespace-nowrap rounded-lg px-3 py-1.5 text-sm text-white"
                  style={{
                    background: video.is_approved ? 'var(--status-critical)' : 'var(--status-good)',
                  }}
                >
                  {video.is_approved ? 'Заблокировать' : 'Одобрить'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
