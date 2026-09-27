import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getChildren } from '../api/client'
import type { ChildProfile } from '../types'

const AVATAR_EMOJI = ['🦉', '🐻', '🦊', '🐨']

export default function ProfileSelect() {
  const [children, setChildren] = useState<ChildProfile[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    getChildren()
      .then(setChildren)
      .catch(() => setError('Не удалось загрузить профили. Проверьте подключение к серверу.'))
  }, [])

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-2xl text-rose-300">
        {error}
      </div>
    )
  }

  if (!children) {
    return (
      <div className="flex h-full items-center justify-center text-3xl text-slate-400">Загрузка…</div>
    )
  }

  if (children.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-2xl text-slate-300">
        Профили не созданы. Попросите родителей добавить профиль через Telegram-бота.
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-10 bg-slate-950 p-8">
      <h1 className="text-4xl font-bold text-white">Кто сегодня смотрит?</h1>
      <div className="flex flex-wrap justify-center gap-10">
        {children.map((child, index) => (
          <button
            key={child.id}
            onClick={() => navigate(`/play/${child.id}`)}
            style={{ minWidth: 220, minHeight: 220 }}
            className="flex flex-col items-center gap-4 rounded-[48px] bg-indigo-600 p-10 shadow-2xl transition-transform active:scale-95"
          >
            {child.avatar_url ? (
              <img
                src={child.avatar_url}
                alt={child.name}
                className="h-32 w-32 rounded-full object-cover"
              />
            ) : (
              <span className="text-8xl">{AVATAR_EMOJI[index % AVATAR_EMOJI.length]}</span>
            )}
            <span className="text-3xl font-semibold text-white">{child.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
