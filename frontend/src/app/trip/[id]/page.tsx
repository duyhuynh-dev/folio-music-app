"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import TripMap, { type Moment } from "@/components/TripMap";
import ReplayPlayer from "@/components/ReplayPlayer";
import { fetchTrip, type TripWithMoments } from "@/lib/trips";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

function toMapMoments(data: TripWithMoments): Moment[] {
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

export default function TripPage() {
  const params = useParams<{ id: string }>();
  const [trip, setTrip] = useState<TripWithMoments | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrip(params.id)
      .then(setTrip)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  const handleMomentChange = useCallback(() => {
    // Could fly-to the moment on the map here
  }, []);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-zinc-400 text-sm">
        Loading trip...
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div className="flex flex-1 items-center justify-center text-red-500 text-sm">
        {error || "Trip not found"}
      </div>
    );
  }

  const moments = toMapMoments(trip);

  return (
    <div className="flex flex-col flex-1 font-sans">
      {/* Header */}
      <header className="px-6 py-6 border-b border-zinc-200 dark:border-zinc-800">
        <h1 className="text-2xl font-bold">{trip.trip.title}</h1>
        {(trip.trip.start_date || trip.trip.end_date) && (
          <p className="text-sm text-zinc-500 mt-1">
            {trip.trip.start_date} — {trip.trip.end_date}
          </p>
        )}
        {trip.trip.members.length > 0 && (
          <p className="text-xs text-zinc-400 mt-1">
            {trip.trip.members.join(", ")}
          </p>
        )}
      </header>

      {/* Map */}
      <div className="flex-1 min-h-[50vh]">
        {MAPBOX_TOKEN && moments.length > 0 ? (
          <TripMap moments={moments} accessToken={MAPBOX_TOKEN} />
        ) : (
          <div className="flex items-center justify-center h-full text-zinc-400 text-sm">
            {moments.length === 0
              ? "No moments with GPS data yet"
              : "Set NEXT_PUBLIC_MAPBOX_TOKEN to view the map"}
          </div>
        )}
      </div>

      {/* Replay + CTA */}
      <div className="px-6 py-6 border-t border-zinc-200 dark:border-zinc-800 space-y-6">
        <ReplayPlayer
          moments={moments}
          onMomentChange={handleMomentChange}
        />

        <div className="text-center">
          <Link
            href="/"
            className="inline-block px-6 py-2.5 rounded-full bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Make your own trip soundtrack
          </Link>
        </div>
      </div>
    </div>
  );
}
