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

export async function fetchDeveloperToken(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/token`);
  if (!res.ok) throw new Error("Failed to fetch developer token");
  const data = await res.json();
  return data.token;
}

export async function suggestMusic(
  photo: File,
  musicUserToken: string,
  variationSeed: number = 0
): Promise<SuggestMusicResponse> {
  const form = new FormData();
  form.append("photo", photo);
  form.append("music_user_token", musicUserToken);
  form.append("variation_seed", String(variationSeed));

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
