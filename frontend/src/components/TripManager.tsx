"use client";

import { useCallback, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Trip {
  id: string;
  title: string;
}

interface TripManagerProps {
  userId: string;
  onTripCreated: (trip: Trip) => void;
  currentTrip: Trip | null;
}

export default function TripManager({
  userId,
  onTripCreated,
  currentTrip,
}: TripManagerProps) {
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleCreate = useCallback(async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const form = new FormData();
      form.append("title", title.trim());
      form.append("user_id", userId);

      const res = await fetch(`${API_BASE}/api/trips`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error("Failed to create trip");
      const data = await res.json();
      onTripCreated(data.trip);
      setTitle("");
      setShowForm(false);
    } catch {
      // silent for now
    } finally {
      setCreating(false);
    }
  }, [title, userId, onTripCreated]);

  if (currentTrip) {
    return (
      <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        <span>Adding to:</span>
        <span className="font-medium text-zinc-800 dark:text-zinc-200">
          {currentTrip.title}
        </span>
      </div>
    );
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
      >
        + Start a new trip
      </button>
    );
  }

  return (
    <div className="flex gap-2 items-center w-full max-w-lg">
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Trip name (e.g. Iceland 2026)"
        className="flex-1 px-3 py-2 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        onKeyDown={(e) => e.key === "Enter" && handleCreate()}
      />
      <button
        onClick={handleCreate}
        disabled={creating || !title.trim()}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 disabled:opacity-50"
      >
        {creating ? "..." : "Create"}
      </button>
      <button
        onClick={() => setShowForm(false)}
        className="text-sm text-zinc-400 hover:text-zinc-600"
      >
        Cancel
      </button>
    </div>
  );
}
