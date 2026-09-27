import { useState } from 'react'
import type { DailyStat } from '../types'

interface WatchMinutesChartProps {
  data: DailyStat[]
}

const WEEKDAY_FORMATTER = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' })

function formatWeekday(isoDate: string): string {
  return WEEKDAY_FORMATTER.format(new Date(`${isoDate}T00:00:00`)).replace('.', '')
}

/**
 * Столбчатый чарт просмотренных минут по дням (одна серия — легенда не
 * нужна, заголовок уже называет метрику). Спеки — dataviz skill:
 * колонки <=24px, 4px скругление сверху, hairline-база, прямая подпись
 * только на последнем (сегодняшнем) баре, остальные — через tooltip по
 * тапу/ховеру. Табличный вид — обязательный accessibility-fallback.
 */
export default function WatchMinutesChart({ data }: WatchMinutesChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const [showTable, setShowTable] = useState(false)

  const maxMinutes = Math.max(1, ...data.map((d) => d.watched_minutes))
  const lastIndex = data.length - 1

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          Минуты просмотра за неделю
        </h3>
        <button
          onClick={() => setShowTable((v) => !v)}
          className="text-xs underline"
          style={{ color: 'var(--text-secondary)' }}
        >
          {showTable ? 'Показать график' : 'Показать таблицей'}
        </button>
      </div>

      {showTable ? (
        <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className="text-left font-normal">День</th>
              <th className="text-right font-normal">Минуты</th>
              <th className="text-right font-normal">Точность квизов</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.stat_date} style={{ borderTop: '1px solid var(--gridline)' }}>
                <td className="py-1">{d.stat_date}</td>
                <td className="py-1 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {d.watched_minutes}
                </td>
                <td className="py-1 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {d.quiz_accuracy !== null ? `${Math.round(d.quiz_accuracy * 100)}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="relative flex h-36 items-end justify-between gap-2 px-1">
          {data.map((d, index) => {
            const heightPct = Math.max((d.watched_minutes / maxMinutes) * 100, 2)
            const isActive = activeIndex === index

            return (
              <div key={d.stat_date} className="flex flex-1 flex-col items-center gap-1">
                <div className="relative flex h-28 w-full items-end justify-center">
                  {isActive && (
                    <div
                      className="absolute -top-8 z-10 whitespace-nowrap rounded-md px-2 py-1 text-xs shadow-md"
                      style={{ background: 'var(--surface-1)', color: 'var(--text-primary)', border: '1px solid var(--gridline)' }}
                    >
                      {d.watched_minutes} мин
                      {d.quiz_accuracy !== null ? ` · ${Math.round(d.quiz_accuracy * 100)}%` : ''}
                    </div>
                  )}
                  <button
                    onMouseEnter={() => setActiveIndex(index)}
                    onMouseLeave={() => setActiveIndex(null)}
                    onClick={() => setActiveIndex(isActive ? null : index)}
                    className="w-full max-w-[24px] rounded-t-[4px] transition-opacity"
                    style={{
                      height: `${heightPct}%`,
                      background: 'var(--series-1)',
                      opacity: isActive ? 0.85 : 1,
                    }}
                    aria-label={`${d.stat_date}: ${d.watched_minutes} минут`}
                  />
                </div>
                {index === lastIndex && (
                  <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                    {d.watched_minutes}
                  </span>
                )}
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {formatWeekday(d.stat_date)}
                </span>
              </div>
            )
          })}
          <div
            className="pointer-events-none absolute bottom-6 left-0 right-0"
            style={{ borderTop: '1px solid var(--baseline)' }}
          />
        </div>
      )}
    </div>
  )
}
