"use client";

import { useCallback, useRef, useState } from "react";
import type { TrackSuggestion } from "@/lib/api";

interface MusicPickerProps {
  suggestions: TrackSuggestion[];
  onPickTrack: (track: TrackSuggestion) => void;
  onTryDifferentVibe: () => void;
  loading?: boolean;
}

function TrackCard({
  track,
  onPick,
}: {
  track: TrackSuggestion;
  onPick: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const togglePreview = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!track.preview_url) return;
      const audio = audioRef.current;
      if (!audio) return;
      if (playing) {
        audio.pause();
        setPlaying(false);
      } else {
        audio.play();
        setPlaying(true);
      }
    },
    [playing, track.preview_url]
  );

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-200 dark:border-zinc-800 p-4 hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">{track.name}</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
            {track.artist}
          </p>
        </div>
        {track.preview_url && (
          <button
            onClick={togglePreview}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
          >
            {playing ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>
        )}
      </div>
      <p className="text-xs text-zinc-600 dark:text-zinc-300 italic leading-snug">
        {track.reason}
      </p>
      <button
        onClick={onPick}
        className="mt-1 w-full text-xs font-medium py-2 rounded-lg bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 hover:opacity-90 transition-opacity"
      >
        Use this one
      </button>
      {track.preview_url && (
        <audio
          ref={audioRef}
          src={track.preview_url}
          onEnded={() => setPlaying(false)}
        />
      )}
    </div>
  );
}

export default function MusicPicker({
  suggestions,
  onPickTrack,
  onTryDifferentVibe,
  loading = false,
}: MusicPickerProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-zinc-500 dark:text-zinc-400">
        <div className="w-6 h-6 border-2 border-zinc-300 dark:border-zinc-600 border-t-zinc-600 dark:border-t-zinc-300 rounded-full animate-spin" />
        <p className="text-sm">Reading the scene...</p>
      </div>
    );
  }

  if (suggestions.length === 0) return null;

  return (
    <div className="w-full max-w-lg flex flex-col gap-4">
      <h2 className="text-lg font-semibold">Your soundtrack</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {suggestions.map((track) => (
          <TrackCard
            key={track.id}
            track={track}
            onPick={() => onPickTrack(track)}
          />
        ))}
      </div>
      <button
        onClick={onTryDifferentVibe}
        className="self-center text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 underline underline-offset-4 transition-colors"
      >
        Try a different vibe
      </button>
    </div>
  );
}
