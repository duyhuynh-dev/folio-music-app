"use client";

import { useCallback, useState } from "react";
import PhotoUpload from "@/components/PhotoUpload";
import MusicPicker from "@/components/MusicPicker";
import { logTasteSignal, suggestMusic, type TrackSuggestion } from "@/lib/api";

const USER_ID_STORAGE_KEY = "folio_user_id";

function getOrCreateUserId(): string {
  if (typeof window === "undefined") return "";

  const existing = window.localStorage.getItem(USER_ID_STORAGE_KEY);
  if (existing) return existing;

  const generated =
    typeof window.crypto !== "undefined" && "randomUUID" in window.crypto
      ? window.crypto.randomUUID()
      : `folio-${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;
  window.localStorage.setItem(USER_ID_STORAGE_KEY, generated);
  return generated;
}

export default function Home() {
  const [suggestions, setSuggestions] = useState<TrackSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [variationSeed, setVariationSeed] = useState(0);
  const [pickedTrack, setPickedTrack] = useState<TrackSuggestion | null>(null);
  const [scene, setScene] = useState<Record<string, unknown> | null>(null);
  const [userId, setUserId] = useState(() => getOrCreateUserId());

  const runPipeline = useCallback(
    async (file: File, seed: number) => {
      setLoading(true);
      setError(null);
      setSuggestions([]);
      setPickedTrack(null);

      const effectiveUserId = userId || getOrCreateUserId();
      if (!userId && effectiveUserId) {
        setUserId(effectiveUserId);
      }

      try {
        const result = await suggestMusic(file, seed, effectiveUserId);
        setScene(result.scene || null);
        setSuggestions(result.suggestions);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    [userId]
  );

  const handlePhotoSelected = useCallback(
    (file: File) => {
      setCurrentFile(file);
      setVariationSeed(0);
      runPipeline(file, 0);
    },
    [runPipeline]
  );

  const handleTryDifferentVibe = useCallback(() => {
    if (!currentFile) return;

    const effectiveUserId = userId || getOrCreateUserId();
    if (effectiveUserId) {
      void Promise.allSettled(
        suggestions.map((track) =>
          logTasteSignal({
            userId: effectiveUserId,
            track,
            action: "try_different",
            scene,
          })
        )
      );
    }

    const newSeed = variationSeed + 1;
    setVariationSeed(newSeed);
    runPipeline(currentFile, newSeed);
  }, [currentFile, variationSeed, runPipeline, scene, suggestions, userId]);

  const handlePickTrack = useCallback((track: TrackSuggestion) => {
    setPickedTrack(track);
    const effectiveUserId = userId || getOrCreateUserId();
    if (!effectiveUserId) return;

    void logTasteSignal({
      userId: effectiveUserId,
      track,
      action: "accept",
      scene,
    }).catch(() => false);
  }, [scene, userId]);

  return (
    <div className="flex flex-col flex-1 items-center bg-zinc-50 dark:bg-black font-sans">
      <main className="flex flex-1 w-full max-w-2xl flex-col items-center gap-8 py-16 px-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight">Folio</h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Your travels, set to music
          </p>
        </div>

        <PhotoUpload
          onPhotoSelected={handlePhotoSelected}
          disabled={loading}
        />

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        {pickedTrack ? (
          <div className="w-full max-w-lg rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950 p-4 text-center">
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Pinned: {pickedTrack.name} — {pickedTrack.artist}
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-1 italic">
              {pickedTrack.reason}
            </p>
          </div>
        ) : (
          <MusicPicker
            suggestions={suggestions}
            onPickTrack={handlePickTrack}
            onTryDifferentVibe={handleTryDifferentVibe}
            loading={loading}
          />
        )}
      </main>
    </div>
  );
}
