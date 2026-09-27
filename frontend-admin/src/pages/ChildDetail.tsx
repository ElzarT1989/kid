import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getChildStats, getWatchHistory } from '../api/client'
import StatTile from '../components/StatTile'
import WatchMinutesChart from '../components/WatchMinutesChart'
import type { ChildStats, WatchHistoryItem } from '../types'

export default function ChildDetail() {
  const { childId } = useParams<{ childId: string }>()
  const id = Number(childId)

  const [stats, setStats] = useState<ChildStats | null>(null)
  const [history, setHistory] = useState<WatchHistoryItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getChildStats(id), getWatchHistory(id)])
      .then(([statsResult, historyResult]) => {
        setStats(statsResult)
        setHistory(historyResult)
      })
      .catch(() => setError('Не удалось загрузить данные профиля'))
  }, [id])

  if (error) return <p style={{ color: 'var(--status-critical)' }}>{error}</p>
  if (!stats) return <p style={{ color: 'var(--text-secondary)' }}>Загрузка…</p>

  return (
    <div className="flex flex-col gap-4">
      <Link to="/" className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        ← Ко всем профилям
      </Link>

      <div className="grid grid-cols-2 gap-2">
        <StatTile label="Сегодня" value={`${stats.today_watched_minutes}/${stats.daily_limit_minutes} мин`} />
        <StatTile label="Осталось сегодня" value={`${stats.today_remaining_minutes} мин`} />
      </div>

      {stats.current_topic && (
        <div className="rounded-xl border p-3" style={{ borderColor: 'var(--gridline)' }}>
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Текущая тема (месяц {stats.current_topic.month}, неделя {stats.current_topic.week})
          </div>
          <div className="font-medium">{stats.current_topic.topic}</div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Статус: {STATUS_LABELS[stats.current_topic.status] ?? stats.current_topic.status}
          </div>
        </div>
      )}

      <div className="rounded-2xl border p-4" style={{ borderColor: 'var(--gridline)', background: 'var(--surface-1)' }}>
        <WatchMinutesChart data={stats.daily_breakdown} />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold">История просмотров</h2>
        <div className="flex flex-col gap-1">
          {history.length === 0 && (
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Пока ничего не просмотрено.
            </p>
          )}
          {history.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: 'var(--gridline)' }}
            >
              <div>
                <div>{item.video_title}</div>
                <div style={{ color: 'var(--text-muted)' }}>
                  {new Date(item.timestamp).toLocaleString('ru-RU')} · {Math.round(item.watched_seconds / 60)} мин
                </div>
              </div>
              <span
                style={{
                  color: item.quiz_passed ? 'var(--status-good)' : 'var(--text-muted)',
                }}
              >
                {item.quiz_passed ? '✓ квиз пройден' : `попыток: ${item.attempts_count}`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const STATUS_LABELS: Record<string, string> = {
  planned: 'запланирована',
  active: 'изучается',
  mastered: 'освоена',
  needs_review: 'требует повторения',
}
