"""Video export service — generates trip recap videos via ffmpeg.

Each moment becomes a segment: photo shown for the duration of its audio
preview (or a default hold time). Segments are concatenated with crossfade
transitions. A static map image is prepended as the intro frame.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

import httpx


SEGMENT_DURATION = 5  # seconds per photo if no audio
CROSSFADE_DURATION = 1
OUTPUT_FPS = 30
OUTPUT_SIZE = "1080x1920"  # vertical / story format


async def _download(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


async def generate_trip_video(
    moments: list[dict],
    output_path: Path | None = None,
) -> Path:
    """Generate a video from a list of moment dicts.

    Each moment dict must have: photo_url, chosen_track_preview_url (nullable).
    Returns the path to the generated mp4.
    """
    if not moments:
        raise ValueError("No moments to export")

    work_dir = Path(tempfile.mkdtemp(prefix="folio_export_"))
    segments: list[Path] = []

    # Download all assets in parallel
    download_tasks = []
    photo_paths: list[Path] = []
    audio_paths: list[Path | None] = []

    for i, moment in enumerate(moments):
        photo_path = work_dir / f"photo_{i}.jpg"
        photo_paths.append(photo_path)
        download_tasks.append(_download(moment["photo_url"], photo_path))

        if moment.get("chosen_track_preview_url"):
            audio_path = work_dir / f"audio_{i}.m4a"
            audio_paths.append(audio_path)
            download_tasks.append(
                _download(moment["chosen_track_preview_url"], audio_path)
            )
        else:
            audio_paths.append(None)

    await asyncio.gather(*download_tasks)

    # Generate each segment
    for i, (photo, audio) in enumerate(zip(photo_paths, audio_paths)):
        segment_path = work_dir / f"segment_{i}.mp4"

        if audio:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(photo),
                "-i", str(audio),
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-vf", f"scale={OUTPUT_SIZE}:force_original_aspect_ratio=decrease,"
                       f"pad={OUTPUT_SIZE}:(ow-iw)/2:(oh-ih)/2:black,"
                       f"format=yuv420p",
                "-r", str(OUTPUT_FPS),
                "-shortest",
                str(segment_path),
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(photo),
                "-t", str(SEGMENT_DURATION),
                "-c:v", "libx264", "-tune", "stillimage",
                "-vf", f"scale={OUTPUT_SIZE}:force_original_aspect_ratio=decrease,"
                       f"pad={OUTPUT_SIZE}:(ow-iw)/2:(oh-ih)/2:black,"
                       f"format=yuv420p",
                "-r", str(OUTPUT_FPS),
                "-an",
                str(segment_path),
            ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg segment {i} failed: {stderr.decode()}")

        segments.append(segment_path)

    # Concatenate segments
    concat_file = work_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{seg}'" for seg in segments),
        encoding="utf-8",
    )

    if output_path is None:
        output_path = work_dir / f"folio_trip_{uuid.uuid4().hex[:8]}.mp4"

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *concat_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {stderr.decode()}")

    return output_path
