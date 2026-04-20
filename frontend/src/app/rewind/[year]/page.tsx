"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import TripMap, { type Moment } from "@/components/TripMap";
import ReplayPlayer from "@/components/ReplayPlayer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

interface RewindData {
  year: number;
  total_trips: number;
  total_moments: number;
  trips: Array<{ id: string; title: string }>;
  moments: Array<{
    id: string;
    photo_url: string;
    chosen_track_name: string | null;
    chosen_track_artist: string | null;
    chosen_track_reason: string | null;
    chosen_track_preview_url: string | null;
    latitude: number | null;
    longitude: number | null;
    taken_at: string | null;
  }>;
}

// TODO: replace with real user ID from auth
const TEMP_USER_ID = "me";

function toMapMoments(data: RewindData): Moment[] {
  return data.moments
    .filter((m) => m.latitude != null && m.longitude != null)
    .map((m) => ({
      id: m.id,
      photoUrl: m.photo_url,
      trackName: m.chosen_track_name || "Untitled",
      trackArtist: m.chosen_track_artist || "Unknown",
      trackReason: m.chosen_track_reason || "",
      trackPreviewUrl: m.chosen_track_preview_url,
      latitude: m.latitude!,
      longitude: m.longitude!,
      takenAt: m.taken_at,
    }));
}

export default function RewindPage() {
  const params = useParams<{ year: string }>();
  const [data, setData] = useState<RewindData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/rewind/${TEMP_USER_ID}/${params.year}`)
      .then((res) => {
        if (!res.ok) throw new Error("No data for this year");
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.year]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-zinc-400 text-sm">
        Loading your year...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-1 items-center justify-center text-red-500 text-sm">
        {error || "Nothing to show"}
      </div>
    );
  }

  const moments = toMapMoments(data);

  return (
    <div className="flex flex-col flex-1 font-sans">
      <header className="px-6 py-8 text-center border-b border-zinc-200 dark:border-zinc-800">
        <p className="text-sm text-zinc-500 uppercase tracking-widest">
          Your year in music
        </p>
        <h1 className="text-5xl font-bold mt-2">{data.year}</h1>
        <div className="flex justify-center gap-6 mt-4 text-sm text-zinc-500">
          <span>
            <strong className="text-zinc-800 dark:text-zinc-200">
              {data.total_trips}
            </strong>{" "}
            trips
          </span>
          <span>
            <strong className="text-zinc-800 dark:text-zinc-200">
              {data.total_moments}
            </strong>{" "}
            moments
          </span>
        </div>
      </header>

      {/* All-year map */}
      <div className="flex-1 min-h-[50vh]">
        {MAPBOX_TOKEN && moments.length > 0 ? (
          <TripMap moments={moments} accessToken={MAPBOX_TOKEN} />
        ) : (
          <div className="flex items-center justify-center h-full text-zinc-400 text-sm">
            {moments.length === 0
              ? "No moments with GPS data"
              : "Set NEXT_PUBLIC_MAPBOX_TOKEN to view the map"}
          </div>
        )}
      </div>

      {/* Replay all moments */}
      <div className="px-6 py-6 border-t border-zinc-200 dark:border-zinc-800">
        <ReplayPlayer moments={moments} />
      </div>
    </div>
  );
}
