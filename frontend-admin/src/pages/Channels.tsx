import { useEffect, useState } from 'react'
import { createChannel, deactivateChannel, getChannels } from '../api/client'
import type { ChannelSource, Platform } from '../types'

export default function Channels() {
  const [channels, setChannels] = useState<ChannelSource[]>([])
  const [loading, setLoading] = useState(true)

  const [platform, setPlatform] = useState<Platform>('youtube')
  const [externalId, setExternalId] = useState('')
  const [channelName, setChannelName] = useState('')
  const [targetAge, setTargetAge] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)

  const load = () => {
    setLoading(true)
    getChannels(false)
      .then(setChannels)
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    try {
      await createChannel({
        platform,
        external_id: externalId,
        channel_name: channelName || undefined,
        target_age_group: targetAge ? Number(targetAge) : undefined,
      })
      setExternalId('')
      setChannelName('')
      setTargetAge('')
      load()
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeactivate = async (id: number) => {
    await deactivateChannel(id)
    load()
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Белый список каналов</h1>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-2 rounded-xl border p-3"
        style={{ borderColor: 'var(--gridline)' }}
      >
        <div className="flex gap-2">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value as Platform)}
            className="rounded-lg border px-3 py-2"
            style={{ borderColor: 'var(--gridline)' }}
          >
            <option value="youtube">YouTube</option>
            <option value="vk">VK Видео</option>
          </select>
          <input
            placeholder="ID канала (например, @ChannelName)"
            value={externalId}
            onChange={(e) => setExternalId(e.target.value)}
            required
            className="flex-1 rounded-lg border px-3 py-2"
            style={{ borderColor: 'var(--gridline)' }}
          />
        </div>
        <div className="flex gap-2">
          <input
            placeholder="Название (необязательно)"
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
            className="flex-1 rounded-lg border px-3 py-2"
            style={{ borderColor: 'var(--gridline)' }}
          />
          <select
            value={targetAge}
            onChange={(e) => setTargetAge(e.target.value)}
            className="rounded-lg border px-3 py-2"
            style={{ borderColor: 'var(--gridline)' }}
          >
            <option value="">Оба возраста</option>
            <option value="2">2 года</option>
            <option value="5">5 лет</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg px-3 py-2 text-white disabled:opacity-50"
          style={{ background: 'var(--series-1)' }}
        >
          Добавить канал
        </button>
      </form>

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Загрузка…</p>
      ) : (
        <div className="flex flex-col gap-2">
          {channels.length === 0 && (
            <p style={{ color: 'var(--text-secondary)' }}>Каналов пока нет.</p>
          )}
          {channels.map((channel) => (
            <div
              key={channel.id}
              className="flex items-center justify-between rounded-lg border px-3 py-2"
              style={{ borderColor: 'var(--gridline)', opacity: channel.is_active ? 1 : 0.5 }}
            >
              <div>
                <div className="font-medium">
                  [{channel.platform}] {channel.channel_name || channel.external_id}
                </div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {channel.target_age_group ? `${channel.target_age_group} лет` : 'оба возраста'}
                  {!channel.is_active && ' · отключён'}
                </div>
              </div>
              {channel.is_active && (
                <button
                  onClick={() => handleDeactivate(channel.id)}
                  className="text-sm"
                  style={{ color: 'var(--status-critical)' }}
                >
                  Отключить
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
