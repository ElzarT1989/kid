import { useEffect, useRef, useState } from 'react'
import type { Quiz } from '../types'

interface QuizOverlayProps {
  quiz: Quiz
  ageGroup: number
  onComplete: (result: { passed: boolean; attempts: number }) => void
}

const CARD_COLORS = ['bg-sky-500', 'bg-emerald-500', 'bg-amber-500', 'bg-rose-500']
const CORRECT_ANSWER_DELAY_MS = 1400

/**
 * Квиз-пауза между роликами (см. SPEC.md, Модуль 3). Вопрос озвучивается
 * через уже готовый .mp3 (tts.py, Этап 2) — синтеза "на лету" здесь нет.
 * При ошибке ребёнок не штрафуется: неверно нажатая карточка просто
 * гаснет, а верный вариант подсвечивается, пока он не будет выбран.
 */
export default function QuizOverlay({ quiz, ageGroup, onComplete }: QuizOverlayProps) {
  const [wrongIndices, setWrongIndices] = useState<Set<number>>(new Set())
  const [attempts, setAttempts] = useState(0)
  const [solved, setSolved] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    // Компонент ремонтируется через key={quiz.id} в ChildPlayer при смене
    // вопроса, так что состояние выше уже сброшено initial-значениями useState.
    audioRef.current?.play().catch(() => {
      /* автозапуск аудио может требовать взаимодействия — не критично */
    })
  }, [quiz.id])

  const handlePick = (index: number) => {
    if (solved) return

    const nextAttempts = attempts + 1
    setAttempts(nextAttempts)

    if (index === quiz.correct_option_index) {
      setSolved(true)
      setTimeout(
        () => onComplete({ passed: nextAttempts === 1, attempts: nextAttempts }),
        CORRECT_ANSWER_DELAY_MS,
      )
    } else {
      setWrongIndices((prev) => new Set(prev).add(index))
    }
  }

  const showText = ageGroup > 3
  const highlightCorrect = solved || wrongIndices.size > 0

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-8 bg-slate-950/95 p-6 text-center">
      {quiz.audio_url && <audio ref={audioRef} src={quiz.audio_url} />}

      {showText && <p className="max-w-2xl text-3xl font-bold text-white">{quiz.question_text}</p>}

      <div className="grid w-full max-w-3xl grid-cols-2 gap-6">
        {quiz.options.map((option, index) => {
          const isCorrect = index === quiz.correct_option_index
          const isWrongPick = wrongIndices.has(index)

          return (
            <button
              key={option.label + index}
              onClick={() => handlePick(index)}
              disabled={solved}
              className={`flex min-h-[140px] flex-col items-center justify-center gap-2 rounded-3xl p-6 shadow-xl transition-transform active:scale-95 ${CARD_COLORS[index % CARD_COLORS.length]} ${
                isCorrect && highlightCorrect ? 'scale-105 ring-8 ring-yellow-300' : ''
              } ${isWrongPick ? 'opacity-40' : ''}`}
            >
              <span className="text-6xl">{option.emoji}</span>
              {showText && <span className="text-xl font-semibold text-white">{option.label}</span>}
            </button>
          )
        })}
      </div>

      {solved && (
        <div className="text-5xl" aria-hidden="true">
          ⭐️⭐️⭐️
        </div>
      )}
    </div>
  )
}
