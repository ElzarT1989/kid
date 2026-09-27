import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getChild, getTodayPlaylist, getVideoQuizzes, mediaUrl, postWatchLog } from '../api/client'
import QuizOverlay from '../components/QuizOverlay'
import VideoPlayer from '../components/VideoPlayer'
import type { PlaylistVideo, Quiz, TodayPlaylist } from '../types'

type Stage = 'loading' | 'playing' | 'quiz' | 'done' | 'error'

export default function ChildPlayer() {
  const { childId } = useParams<{ childId: string }>()
  const navigate = useNavigate()
  const id = Number(childId)

  const [childAge, setChildAge] = useState(5)
  const [playlist, setPlaylist] = useState<TodayPlaylist | null>(null)
  const [itemIndex, setItemIndex] = useState(0)
  const [quizzes, setQuizzes] = useState<Quiz[] | null>(null)
  const [quizIndex, setQuizIndex] = useState(0)
  const [watchedSeconds, setWatchedSeconds] = useState(0)
  const [firstAttemptPassed, setFirstAttemptPassed] = useState(true)
  const [totalAttempts, setTotalAttempts] = useState(0)
  const [stage, setStage] = useState<Stage>('loading')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setStage('error')
      setErrorMessage('Некорректный профиль')
      return
    }

    Promise.all([getChild(id), getTodayPlaylist(id)])
      .then(([child, data]) => {
        setChildAge(child.age)
        setPlaylist(data)
        setStage(data.items.length > 0 ? 'playing' : 'done')
      })
      .catch(() => {
        setStage('error')
        setErrorMessage('Плейлист на сегодня ещё не готов. Попросите родителей настроить его.')
      })
  }, [id])

  const currentItem: PlaylistVideo | undefined = playlist?.items[itemIndex]

  const finishVideoAndLog = useCallback(
    async (video: PlaylistVideo, quizPassedOverall: boolean, attempts: number) => {
      try {
        await postWatchLog(id, {
          video_id: video.video_id,
          watched_seconds: watchedSeconds,
          completed: true,
          skipped: false,
          quiz_passed: quizPassedOverall,
          attempts_count: Math.max(attempts, 1),
        })
      } catch {
        // Сетевая ошибка логирования не должна останавливать просмотр ребёнком.
      }
    },
    [id, watchedSeconds],
  )

  const goToNextItem = useCallback(() => {
    setQuizzes(null)
    if (!playlist || itemIndex + 1 >= playlist.items.length) {
      setStage('done')
      return
    }
    setItemIndex((prev) => prev + 1)
    setWatchedSeconds(0)
    setStage('playing')
  }, [itemIndex, playlist])

  const handleVideoEnded = useCallback(
    (seconds: number) => {
      setWatchedSeconds(seconds)
      if (!currentItem) return

      getVideoQuizzes(currentItem.video_id)
        .then((data) => {
          if (data.length === 0) {
            void finishVideoAndLog(currentItem, true, 1)
            goToNextItem()
            return
          }
          setQuizzes(data)
          setQuizIndex(0)
          setFirstAttemptPassed(true)
          setTotalAttempts(0)
          setStage('quiz')
        })
        .catch(() => {
          void finishVideoAndLog(currentItem, true, 1)
          goToNextItem()
        })
    },
    [currentItem, finishVideoAndLog, goToNextItem],
  )

  const handleQuizComplete = useCallback(
    (result: { passed: boolean; attempts: number }) => {
      if (!currentItem || !quizzes) return

      const overallPassed = firstAttemptPassed && result.passed
      const overallAttempts = totalAttempts + result.attempts

      if (quizIndex + 1 < quizzes.length) {
        setFirstAttemptPassed(overallPassed)
        setTotalAttempts(overallAttempts)
        setQuizIndex((prev) => prev + 1)
        return
      }

      void finishVideoAndLog(currentItem, overallPassed, overallAttempts)
      goToNextItem()
    },
    [currentItem, quizzes, quizIndex, firstAttemptPassed, totalAttempts, finishVideoAndLog, goToNextItem],
  )

  if (stage === 'loading') {
    return (
      <div className="flex h-full items-center justify-center text-3xl text-slate-400">Загрузка…</div>
    )
  }

  if (stage === 'error') {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 p-8 text-center">
        <p className="text-2xl text-rose-300">{errorMessage}</p>
        <button
          onClick={() => navigate('/')}
          className="rounded-2xl bg-indigo-600 px-8 py-4 text-xl text-white"
        >
          Назад к профилям
        </button>
      </div>
    )
  }

  if (stage === 'done' || !currentItem) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 p-8 text-center">
        <p className="text-4xl">🎉 На сегодня всё!</p>
        <p className="text-2xl text-slate-300">Увидимся завтра с новыми видео.</p>
        <button
          onClick={() => navigate('/')}
          className="rounded-2xl bg-indigo-600 px-8 py-4 text-xl text-white"
        >
          К выбору профиля
        </button>
      </div>
    )
  }

  const videoSrc = mediaUrl(currentItem.video_url)

  return (
    <div className="relative h-full w-full">
      {stage === 'playing' && videoSrc && (
        <VideoPlayer key={currentItem.video_id} src={videoSrc} onEnded={handleVideoEnded} />
      )}
      {stage === 'quiz' && quizzes && (
        <QuizOverlay
          key={quizzes[quizIndex].id}
          quiz={quizzes[quizIndex]}
          ageGroup={childAge}
          onComplete={handleQuizComplete}
        />
      )}
    </div>
  )
}
