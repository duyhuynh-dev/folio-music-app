const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TrackSuggestion {
  id: string;
  name: string;
  artist: string;
  preview_url: string | null;
  apple_music_url: string | null;
  reason: string;
}

export interface SuggestMusicResponse {
  scene: Record<string, unknown>;
  suggestions: TrackSuggestion[];
}

export async function suggestMusic(
  photo: File,
  variationSeed: number = 0,
  userId: string = ""
): Promise<SuggestMusicResponse> {
  const form = new FormData();
  form.append("photo", photo);
  form.append("variation_seed", String(variationSeed));
  if (userId) {
    form.append("user_id", userId);
  }

  const res = await fetch(`${API_BASE}/api/suggest-music`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Pipeline request failed");
  }

  return res.json();
}

export type TasteAction = "accept" | "reject" | "try_different";

interface LogTasteSignalParams {
  userId: string;
  track: TrackSuggestion;
  action: TasteAction;
  scene?: Record<string, unknown> | null;
}

export async function logTasteSignal({
  userId,
  track,
  action,
  scene,
}: LogTasteSignalParams): Promise<boolean> {
  if (!userId) return false;

  const form = new FormData();
  form.append("user_id", userId);
  form.append("track_id", track.id);
  form.append("track_name", track.name);
  form.append("track_artist", track.artist);
  form.append("action", action);
  form.append("scene_json", JSON.stringify(scene || {}));

  const res = await fetch(`${API_BASE}/api/taste`, {
    method: "POST",
    body: form,
  });

  return res.ok;
}
