import { useEffect, useRef, useState } from 'react'

interface VideoPlayerProps {
  src: string
  onEnded: (watchedSeconds: number) => void
}

/**
 * Изоляция плеера: видео уже скачано локально backend'ом (см. SPEC.md,
 * п.8.1), поэтому вместо YouTube IFrame API используется обычный HTML5
 * <video> — без встроенных нативных控制ов и без риска перехода на внешние
 * ссылки (у local-файла их просто нет). Прозрачный оверлей поверх видео
 * перехватывает клики/долгие нажатия, чтобы ребёнок не мог поставить на
 * паузу, перемотать или вызвать системное меню — ролик должен быть
 * досмотрен целиком.
 */
export default function VideoPlayer({ src, onEnded }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const watchedSecondsRef = useRef(0)
  const [needsTapToStart, setNeedsTapToStart] = useState(false)

  useEffect(() => {
    // Компонент ремонтируется через key={video_id} в ChildPlayer при смене
    // ролика, так что needsTapToStart уже сброшен initial-значением useState.
    watchedSecondsRef.current = 0
    const video = videoRef.current
    if (!video) return
    video.currentTime = 0
    video.play().catch(() => setNeedsTapToStart(true))
  }, [src])

  const handleTapToStart = () => {
    videoRef.current
      ?.play()
      .then(() => setNeedsTapToStart(false))
      .catch(() => {})
  }

  const handleEnded = () => onEnded(Math.round(watchedSecondsRef.current))

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      watchedSecondsRef.current = videoRef.current.currentTime
    }
  }

  return (
    <div className="relative h-full w-full bg-black">
      <video
        ref={videoRef}
        src={src}
        className="h-full w-full object-contain"
        playsInline
        disablePictureInPicture
        disableRemotePlayback
        controlsList="nodownload noremoteplayback nofullscreen"
        onEnded={handleEnded}
        onTimeUpdate={handleTimeUpdate}
        onContextMenu={(event) => event.preventDefault()}
      />

      <div className="absolute inset-0" onContextMenu={(event) => event.preventDefault()} />

      {needsTapToStart && (
        <button
          onClick={handleTapToStart}
          className="absolute inset-0 flex items-center justify-center bg-black/60 text-4xl text-white"
        >
          ▶️ Нажми, чтобы начать
        </button>
      )}
    </div>
  )
}
