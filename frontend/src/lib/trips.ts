const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TripData {
  id: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  members: string[];
  created_at: string;
}

export interface MomentData {
  id: string;
  photo_url: string;
  chosen_track_name: string | null;
  chosen_track_artist: string | null;
  chosen_track_reason: string | null;
  chosen_track_preview_url: string | null;
  chosen_track_apple_url: string | null;
  latitude: number | null;
  longitude: number | null;
  taken_at: string | null;
}

export interface TripWithMoments {
  trip: TripData;
  moments: MomentData[];
}

export async function fetchTrip(tripId: string): Promise<TripWithMoments> {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Trip not found");
  return res.json();
}
