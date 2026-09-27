import { NavLink, useNavigate } from 'react-router-dom'
import { clearToken } from '../api/client'

const LINK_CLASS = 'px-3 py-2 text-sm font-medium rounded-lg'

export default function Nav() {
  const navigate = useNavigate()

  const linkStyle = ({ isActive }: { isActive: boolean }) => ({
    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
    background: isActive ? 'var(--gridline)' : 'transparent',
  })

  return (
    <nav
      className="flex items-center justify-between border-b px-4 py-2"
      style={{ borderColor: 'var(--gridline)', background: 'var(--surface-1)' }}
    >
      <div className="flex gap-1">
        <NavLink to="/" end className={LINK_CLASS} style={linkStyle}>
          Дашборд
        </NavLink>
        <NavLink to="/channels" className={LINK_CLASS} style={linkStyle}>
          Каналы
        </NavLink>
        <NavLink to="/videos" className={LINK_CLASS} style={linkStyle}>
          Видео
        </NavLink>
      </div>
      <button
        onClick={() => {
          clearToken()
          navigate('/login', { replace: true })
        }}
        className="text-sm"
        style={{ color: 'var(--text-secondary)' }}
      >
        Выйти
      </button>
    </nav>
  )
}
