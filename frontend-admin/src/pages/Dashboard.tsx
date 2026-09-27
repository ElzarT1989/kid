import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createChild, getChildren, getChildStats, getSystemStatus } from '../api/client'
import StatTile from '../components/StatTile'
import SystemStatusPanel from '../components/SystemStatusPanel'
import type { ChildProfile, ChildStats, SystemStatus } from '../types'

export default function Dashboard() {
  const [children, setChildren] = useState<ChildProfile[]>([])
  const [stats, setStats] = useState<Record<number, ChildStats>>({})
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)

  const loadAll = () => {
    setLoading(true)
    Promise.all([getChildren(), getSystemStatus()])
      .then(async ([list, status]) => {
        setChildren(list)
        setSystemStatus(status)
        const entries = await Promise.all(
          list.map(async (child) => [child.id, await getChildStats(child.id)] as const),
        )
        setStats(Object.fromEntries(entries))
      })
      .catch(() => setError('Не удалось загрузить данные'))
      .finally(() => setLoading(false))
  }

  const refreshSystemStatus = () => {
    getSystemStatus().then(setSystemStatus).catch(() => {})
  }

  useEffect(loadAll, [])

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Загрузка…</p>
  if (error) return <p style={{ color: 'var(--status-critical)' }}>{error}</p>

  return (
    <div className="flex flex-col gap-4">
      {systemStatus && <SystemStatusPanel status={systemStatus} onIngestStarted={refreshSystemStatus} />}

      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Профили</h1>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="rounded-lg px-3 py-1.5 text-sm text-white"
          style={{ background: 'var(--series-1)' }}
        >
          + Профиль
        </button>
      </div>

      {showAddForm && (
        <AddChildForm
          onCreated={() => {
            setShowAddForm(false)
            loadAll()
          }}
        />
      )}

      {children.length === 0 && (
        <p style={{ color: 'var(--text-secondary)' }}>
          Профили ещё не созданы. Добавьте первый профиль или через Telegram-бота (/add_channel и т.д.).
        </p>
      )}

      {children.map((child) => {
        const childStats = stats[child.id]
        return (
          <Link
            key={child.id}
            to={`/children/${child.id}`}
            className="rounded-2xl border p-4 shadow-sm"
            style={{ borderColor: 'var(--gridline)', background: 'var(--surface-1)' }}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">
                {child.name} <span style={{ color: 'var(--text-muted)' }}>· {child.age} лет</span>
              </h2>
              {childStats?.current_topic && (
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Тема: {childStats.current_topic.topic}
                </span>
              )}
            </div>
            {childStats && (
              <div className="grid grid-cols-3 gap-2">
                <StatTile
                  label="Сегодня"
                  value={`${childStats.today_watched_minutes}/${childStats.daily_limit_minutes} мин`}
                  accent={childStats.today_remaining_minutes <= 0 ? 'warning' : 'neutral'}
                />
                <StatTile label="За неделю" value={`${childStats.week_watched_minutes} мин`} />
                <StatTile
                  label="Точность квизов"
                  value={
                    childStats.week_quiz_accuracy !== null
                      ? `${Math.round(childStats.week_quiz_accuracy * 100)}%`
                      : '—'
                  }
                  accent={
                    childStats.week_quiz_accuracy === null
                      ? 'neutral'
                      : childStats.week_quiz_accuracy >= 0.8
                        ? 'good'
                        : childStats.week_quiz_accuracy <= 0.5
                          ? 'critical'
                          : 'neutral'
                  }
                />
              </div>
            )}
          </Link>
        )
      })}
    </div>
  )
}

function AddChildForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const [age, setAge] = useState(5)
  const [limit, setLimit] = useState(60)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    try {
      await createChild({ name, age, daily_limit_minutes: limit })
      onCreated()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 rounded-xl border p-3"
      style={{ borderColor: 'var(--gridline)' }}
    >
      <input
        placeholder="Имя"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        className="rounded-lg border px-3 py-2"
        style={{ borderColor: 'var(--gridline)' }}
      />
      <div className="flex gap-2">
        <select
          value={age}
          onChange={(e) => setAge(Number(e.target.value))}
          className="flex-1 rounded-lg border px-3 py-2"
          style={{ borderColor: 'var(--gridline)' }}
        >
          <option value={2}>2 года</option>
          <option value={5}>5 лет</option>
        </select>
        <input
          type="number"
          min={5}
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="w-28 rounded-lg border px-3 py-2"
          style={{ borderColor: 'var(--gridline)' }}
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-lg px-3 py-2 text-white disabled:opacity-50"
        style={{ background: 'var(--series-1)' }}
      >
        Создать профиль
      </button>
    </form>
  )
}
