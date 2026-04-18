"use client";

import { useCallback, useRef, useState } from "react";

interface ExifData {
  latitude: number | null;
  longitude: number | null;
  takenAt: string | null;
}

interface PhotoUploadProps {
  onPhotoSelected: (file: File, exif: ExifData) => void;
  disabled?: boolean;
}

function parseExif(file: File): Promise<ExifData> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const view = new DataView(e.target?.result as ArrayBuffer);
      // Basic EXIF extraction — GPS and DateTime
      // For production, use a library like exifr
      resolve({ latitude: null, longitude: null, takenAt: null });
    };
    reader.onerror = () =>
      resolve({ latitude: null, longitude: null, takenAt: null });
    reader.readAsArrayBuffer(file.slice(0, 128 * 1024));
  });
}

export default function PhotoUpload({
  onPhotoSelected,
  disabled = false,
}: PhotoUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith("image/")) return;
      setPreview(URL.createObjectURL(file));
      const exif = await parseExif(file);
      onPhotoSelected(file, exif);
    },
    [onPhotoSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        relative flex flex-col items-center justify-center
        w-full max-w-lg aspect-[4/3] rounded-2xl border-2 border-dashed
        cursor-pointer transition-all
        ${
          dragOver
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
            : "border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-500"
        }
        ${disabled ? "opacity-50 pointer-events-none" : ""}
      `}
    >
      {preview ? (
        <img
          src={preview}
          alt="Selected photo"
          className="absolute inset-0 w-full h-full object-cover rounded-2xl"
        />
      ) : (
        <div className="flex flex-col items-center gap-3 text-zinc-500 dark:text-zinc-400">
          <svg
            className="w-10 h-10"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 16v-8m0 0l-3 3m3-3l3 3M3 16.5V18a2.25 2.25 0 002.25 2.25h13.5A2.25 2.25 0 0021 18v-1.5m-18 0V7.875C3 6.839 3.84 6 4.875 6h2.25L9 3.75h6L16.875 6h2.25C20.16 6 21 6.839 21 7.875V16.5"
            />
          </svg>
          <p className="text-sm font-medium">
            Drop a travel photo here, or tap to browse
          </p>
          <p className="text-xs">JPG, PNG, WebP</p>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}
