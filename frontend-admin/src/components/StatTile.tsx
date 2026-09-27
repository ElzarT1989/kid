interface StatTileProps {
  label: string
  value: string
  accent?: 'good' | 'warning' | 'critical' | 'neutral'
}

const ACCENT_VAR: Record<NonNullable<StatTileProps['accent']>, string> = {
  good: 'var(--status-good)',
  warning: 'var(--status-warning)',
  critical: 'var(--status-critical)',
  neutral: 'var(--text-primary)',
}

/** Stat-tile: label (sentence case) + value (semibold, proportional figures). */
export default function StatTile({ label, value, accent = 'neutral' }: StatTileProps) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: 'var(--gridline)' }}>
      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div className="text-2xl font-semibold" style={{ color: ACCENT_VAR[accent] }}>
        {value}
      </div>
    </div>
  )
}
