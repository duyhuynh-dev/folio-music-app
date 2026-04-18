"use client";

import { useCallback, useState } from "react";
import PhotoUpload from "@/components/PhotoUpload";
import MusicPicker from "@/components/MusicPicker";
import { suggestMusic, type TrackSuggestion } from "@/lib/api";
import { authorizeMusicKit, getMusicUserToken } from "@/lib/musickit";

export default function Home() {
  const [suggestions, setSuggestions] = useState<TrackSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [variationSeed, setVariationSeed] = useState(0);
  const [pickedTrack, setPickedTrack] = useState<TrackSuggestion | null>(null);

  const runPipeline = useCallback(
    async (file: File, seed: number) => {
      setLoading(true);
      setError(null);
      setSuggestions([]);
      setPickedTrack(null);

      try {
        let token = getMusicUserToken() || "";
        if (!token) {
          try {
            token = await authorizeMusicKit();
          } catch {
            // Non-subscriber: proceed without token, previews still work
            token = "";
          }
        }

        const result = await suggestMusic(file, token, seed);
        setSuggestions(result.suggestions);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    []
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
    const newSeed = variationSeed + 1;
    setVariationSeed(newSeed);
    runPipeline(currentFile, newSeed);
  }, [currentFile, variationSeed, runPipeline]);

  const handlePickTrack = useCallback((track: TrackSuggestion) => {
    setPickedTrack(track);
  }, []);

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
