import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/client'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(password)
      navigate('/', { replace: true })
    } catch (err) {
      if (err instanceof Error && err.message.startsWith('401')) {
        setError('Неверный пароль')
      } else if (err instanceof Error && err.message.startsWith('500')) {
        setError('Пароль ещё не настроен на сервере (ADMIN_DASHBOARD_PASSWORD)')
      } else {
        // Сетевая ошибка (backend недоступен/разворачивается) — не путать
        // с неверным паролем, иначе не отличить одно от другого.
        setError('Не удалось подключиться к серверу. Backend недоступен — попробуйте позже.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border p-6 shadow-sm"
        style={{ borderColor: 'var(--gridline)', background: 'var(--surface-1)' }}
      >
        <h1 className="mb-1 text-xl font-semibold">KidsEdu — родительский доступ</h1>
        <p className="mb-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
          Введите общий пароль родительской панели.
        </p>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Пароль"
          autoFocus
          className="mb-3 w-full rounded-lg border px-3 py-2 text-base"
          style={{ borderColor: 'var(--gridline)' }}
        />
        {error && (
          <p className="mb-3 text-sm" style={{ color: 'var(--status-critical)' }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading || password.length === 0}
          className="w-full rounded-lg px-4 py-2 font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--series-1)' }}
        >
          {loading ? 'Проверка…' : 'Войти'}
        </button>
      </form>
    </div>
  )
}
