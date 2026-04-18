"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Moment } from "./TripMap";

interface ReplayPlayerProps {
  moments: Moment[];
  onMomentChange?: (index: number) => void;
}

export default function ReplayPlayer({
  moments,
  onMomentChange,
}: ReplayPlayerProps) {
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = useCallback(() => {
    setPlaying(false);
    setCurrentIndex(-1);
    audioRef.current?.pause();
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const playMoment = useCallback(
    (index: number) => {
      if (index >= moments.length) {
        stop();
        return;
      }

      setCurrentIndex(index);
      onMomentChange?.(index);

      const moment = moments[index];
      const audio = audioRef.current;

      if (audio && moment.trackPreviewUrl) {
        audio.src = moment.trackPreviewUrl;
        audio.play().catch(() => {});
      }

      // Auto-advance after 30s (preview length) or 10s if no preview
      const duration = moment.trackPreviewUrl ? 30000 : 10000;
      timerRef.current = setTimeout(() => playMoment(index + 1), duration);
    },
    [moments, onMomentChange, stop]
  );

  const toggleReplay = useCallback(() => {
    if (playing) {
      stop();
    } else {
      setPlaying(true);
      playMoment(0);
    }
  }, [playing, playMoment, stop]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (moments.length === 0) return null;

  const current = currentIndex >= 0 ? moments[currentIndex] : null;

  return (
    <div className="w-full flex flex-col gap-3">
      {/* Progress bar */}
      <div className="flex gap-1">
        {moments.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i < currentIndex
                ? "bg-blue-500"
                : i === currentIndex
                  ? "bg-blue-400 animate-pulse"
                  : "bg-zinc-200 dark:bg-zinc-800"
            }`}
          />
        ))}
      </div>

      {/* Current moment info */}
      {current && (
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-900">
          <img
            src={current.photoUrl}
            alt=""
            className="w-12 h-12 rounded-lg object-cover"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{current.trackName}</p>
            <p className="text-xs text-zinc-500 truncate">
              {current.trackArtist}
            </p>
          </div>
          <span className="text-xs text-zinc-400 shrink-0">
            {currentIndex + 1} / {moments.length}
          </span>
        </div>
      )}

      {/* Controls */}
      <button
        onClick={toggleReplay}
        className="self-center flex items-center gap-2 px-5 py-2.5 rounded-full bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium hover:opacity-90 transition-opacity"
      >
        {playing ? (
          <>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
            Stop
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
            Replay trip
          </>
        )}
      </button>

      <audio ref={audioRef} />
    </div>
  );
}
