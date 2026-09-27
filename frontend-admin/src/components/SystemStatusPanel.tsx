import { useState } from 'react'
import { runIngestion } from '../api/client'
import type { SystemStatus } from '../types'

interface SystemStatusPanelProps {
  status: SystemStatus
  onIngestStarted: () => void
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
      style={{
        color: ok ? 'var(--status-good)' : 'var(--status-critical)',
        border: `1px solid ${ok ? 'var(--status-good)' : 'var(--status-critical)'}`,
      }}
    >
      {ok ? '✓' : '✕'} {label}
    </span>
  )
}

/**
 * Без ручного триггера ингестии единственный способ наполнить систему
 * видео — запускать ingestor.py из кода напрямую; здесь родитель видит,
 * чего не хватает (ключ Gemini, каналы), и может нажать кнопку.
 */
export default function SystemStatusPanel({ status, onIngestStarted }: SystemStatusPanelProps) {
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)

  const canIngest = status.active_channels_count > 0 && status.gemini_configured

  const handleIngest = async () => {
    setRunning(true)
    setMessage(null)
    try {
      const result = await runIngestion()
      setMessage({
        text: `Запущено для ${result.channels_count} канал(ов). Новые видео появятся на вкладке «Видео» через несколько минут.`,
        isError: false,
      })
      onIngestStarted()
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : 'Не удалось запустить', isError: true })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div
      className="flex flex-col gap-3 rounded-2xl border p-4"
      style={{ borderColor: 'var(--gridline)', background: 'var(--surface-1)' }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge ok={status.gemini_configured} label="Gemini API" />
        <Badge ok={status.telegram_configured} label="Telegram-бот" />
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Каналов: {status.active_channels_count}/{status.channels_count} активно · Видео:{' '}
          {status.videos_approved_count}/{status.videos_total_count} одобрено
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleIngest}
          disabled={running || !canIngest}
          className="rounded-lg px-3 py-1.5 text-sm text-white disabled:opacity-40"
          style={{ background: 'var(--series-1)' }}
        >
          {running ? 'Запускается…' : 'Проверить каналы на новые видео'}
        </button>
        {!canIngest && (
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {status.active_channels_count === 0
              ? 'Сначала добавьте канал на вкладке «Каналы»'
              : 'Нужно настроить GEMINI_API_KEY на сервере'}
          </span>
        )}
      </div>

      {message && (
        <p className="text-sm" style={{ color: message.isError ? 'var(--status-critical)' : 'var(--status-good)' }}>
          {message.text}
        </p>
      )}
    </div>
  )
}
