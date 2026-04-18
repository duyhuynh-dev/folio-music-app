"""Phase 1.6 evaluation harness for Folio.

Two-step workflow:
1. Generate artifacts:
   python eval.py generate ./eval_photos ./eval_output
2. Fill in score_1_to_5 inside eval_output/scores.csv, then summarize:
   python eval.py summarize ./eval_output/run.json ./eval_output/scores.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from pipeline.fetch import fetch_candidates
from pipeline.rank import rank_and_explain
from pipeline.scene import extract_scene
from pipeline.translate import translate_to_music_params

load_dotenv()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class EvalTrack(BaseModel):
    id: str
    name: str
    artist: str
    reason: str
    source: str
    preview_url: str | None = None
    apple_music_url: str | None = None


class EvalPhotoResult(BaseModel):
    photo_name: str
    relative_path: str
    scene: dict[str, object] | None = None
    suggestions: list[EvalTrack] = Field(default_factory=list)
    candidate_count: int = 0
    error: str | None = None


class EvalRun(BaseModel):
    generated_at_utc: str
    photos_dir: str
    total_photos: int
    variation_seed: int
    results: list[EvalPhotoResult] = Field(default_factory=list)


class GateMetrics(BaseModel):
    scored_photos: int
    unscored_photos: int
    high_quality_photos: int
    average_score: float
    quality_ratio: float
    min_good_score: int
    pass_threshold: float
    passed: bool


def find_photo_paths(photos_dir: Path) -> list[Path]:
    if not photos_dir.exists():
        raise RuntimeError(f"Photos directory does not exist: {photos_dir}")
    if not photos_dir.is_dir():
        raise RuntimeError(f"Photos path is not a directory: {photos_dir}")

    photo_paths = sorted(
        path
        for path in photos_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not photo_paths:
        raise RuntimeError(f"No photos found in {photos_dir}")
    return photo_paths


async def evaluate_photo(photo_path: Path, photos_dir: Path, variation_seed: int) -> EvalPhotoResult:
    relative_path = str(photo_path.relative_to(photos_dir))
    base_result = EvalPhotoResult(photo_name=photo_path.name, relative_path=relative_path)

    try:
        image_bytes = photo_path.read_bytes()
        scene = extract_scene(image_bytes)
        params = translate_to_music_params(scene)
        candidates = await fetch_candidates(params)
        ranked = rank_and_explain(scene, candidates, variation_seed=variation_seed)

        return base_result.model_copy(
            update={
                "scene": scene.model_dump(),
                "candidate_count": len(candidates),
                "suggestions": [
                    EvalTrack(
                        id=track.id,
                        name=track.name,
                        artist=track.artist,
                        reason=track.reason,
                        source=next(
                            (candidate.source for candidate in candidates if candidate.id == track.id),
                            "unknown",
                        ),
                        preview_url=track.preview_url,
                        apple_music_url=track.apple_music_url,
                    )
                    for track in ranked
                ],
            }
        )
    except Exception as exc:
        return base_result.model_copy(update={"error": str(exc)})


def build_eval_report(run: EvalRun) -> str:
    success_count = len([result for result in run.results if not result.error])
    lines: list[str] = [
        "# Folio Eval Report",
        "",
        f"- Generated at (UTC): `{run.generated_at_utc}`",
        f"- Photos directory: `{run.photos_dir}`",
        f"- Total photos: `{run.total_photos}`",
        f"- Successful pipeline runs: `{success_count}`",
        "",
    ]

    for result in run.results:
        lines.append(f"## {result.relative_path}")
        lines.append("")
        if result.error:
            lines.append(f"- Status: `error`")
            lines.append(f"- Error: `{result.error}`")
            lines.append("")
            continue

        lines.append("- Status: `ok`")
        lines.append(f"- Candidate count: `{result.candidate_count}`")
        lines.append("- Scene JSON:")
        lines.append("```json")
        lines.append(json.dumps(result.scene, indent=2))
        lines.append("```")
        lines.append("- Final picks:")
        if not result.suggestions:
            lines.append("  - No ranked tracks returned.")
        for track in result.suggestions:
            lines.append(f"  - {track.name} — {track.artist}: {track.reason}")
        lines.append("- Manual score (1-5):")
        lines.append("")

    return "\n".join(lines)


def write_scores_template(run: EvalRun, scores_csv_path: Path) -> None:
    scores_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with scores_csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["photo_name", "score_1_to_5", "notes"])
        for result in run.results:
            if result.error:
                continue
            writer.writerow([result.relative_path, "", ""])


def load_scores(scores_csv_path: Path) -> dict[str, int]:
    if not scores_csv_path.exists():
        raise RuntimeError(f"Scores CSV not found: {scores_csv_path}")

    scores: dict[str, int] = {}
    with scores_csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"photo_name", "score_1_to_5"}
        if not required_columns.issubset(reader.fieldnames or set()):
            raise RuntimeError("Scores CSV must include columns: photo_name, score_1_to_5")

        for row_number, row in enumerate(reader, start=2):
            photo_name = (row.get("photo_name") or "").strip()
            if not photo_name:
                raise RuntimeError(f"Row {row_number}: photo_name is required")
            if photo_name in scores:
                raise RuntimeError(f"Row {row_number}: duplicate photo_name '{photo_name}'")

            raw_score = (row.get("score_1_to_5") or "").strip()
            if not raw_score:
                continue
            try:
                score = int(raw_score)
            except ValueError as exc:
                raise RuntimeError(
                    f"Row {row_number}: score_1_to_5 must be an integer between 1 and 5"
                ) from exc

            if score < 1 or score > 5:
                raise RuntimeError(f"Row {row_number}: score_1_to_5 must be between 1 and 5")
            scores[photo_name] = score
    return scores


def compute_gate_metrics(
    run: EvalRun,
    scores: dict[str, int],
    min_good_score: int,
    pass_threshold: float,
) -> GateMetrics:
    evaluated_photo_names = [result.relative_path for result in run.results if not result.error]
    scored_values: list[int] = []
    high_quality_count = 0
    for photo_name in evaluated_photo_names:
        score = scores.get(photo_name)
        if score is None:
            continue
        scored_values.append(score)
        if score >= min_good_score:
            high_quality_count += 1

    scored_count = len(scored_values)
    unscored_count = len(evaluated_photo_names) - scored_count
    average_score = (sum(scored_values) / scored_count) if scored_count else 0.0
    quality_ratio = (high_quality_count / scored_count) if scored_count else 0.0
    passed = scored_count > 0 and quality_ratio >= pass_threshold

    return GateMetrics(
        scored_photos=scored_count,
        unscored_photos=unscored_count,
        high_quality_photos=high_quality_count,
        average_score=round(average_score, 3),
        quality_ratio=round(quality_ratio, 3),
        min_good_score=min_good_score,
        pass_threshold=pass_threshold,
        passed=passed,
    )


def build_summary_report(run: EvalRun, metrics: GateMetrics) -> str:
    status = "PASS" if metrics.passed else "FAIL"
    lines = [
        "# Folio Phase 1.6 Gate Summary",
        "",
        f"- Gate status: **{status}**",
        f"- Threshold: `{metrics.min_good_score}/5` on at least `{metrics.pass_threshold:.0%}` of scored photos",
        f"- High-quality photos: `{metrics.high_quality_photos}`",
        f"- Scored photos: `{metrics.scored_photos}`",
        f"- Unscored photos: `{metrics.unscored_photos}`",
        f"- Average score: `{metrics.average_score:.2f}`",
        f"- Quality ratio: `{metrics.quality_ratio:.1%}`",
        "",
    ]
    return "\n".join(lines)


async def generate_artifacts(photos_dir: Path, output_dir: Path, variation_seed: int) -> tuple[Path, Path, Path]:
    photo_paths = find_photo_paths(photos_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[EvalPhotoResult] = []
    for photo_path in photo_paths:
        results.append(await evaluate_photo(photo_path, photos_dir, variation_seed=variation_seed))

    run = EvalRun(
        generated_at_utc=datetime.now(UTC).isoformat(),
        photos_dir=str(photos_dir.resolve()),
        total_photos=len(photo_paths),
        variation_seed=variation_seed,
        results=results,
    )

    run_json_path = output_dir / "run.json"
    report_md_path = output_dir / "report.md"
    scores_csv_path = output_dir / "scores.csv"

    run_json_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    report_md_path.write_text(build_eval_report(run), encoding="utf-8")
    write_scores_template(run, scores_csv_path)

    return run_json_path, report_md_path, scores_csv_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Folio Phase 1.6 evaluation harness.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Run pipeline and generate eval artifacts.")
    generate_parser.add_argument("photos_dir", type=Path, help="Directory containing evaluation photos.")
    generate_parser.add_argument("output_dir", type=Path, help="Directory to write report artifacts.")
    generate_parser.add_argument(
        "--variation-seed",
        type=int,
        default=0,
        help="Variation seed passed into stage 4 ranking.",
    )

    summarize_parser = subparsers.add_parser("summarize", help="Compute gate pass/fail from manual scores.")
    summarize_parser.add_argument("run_json", type=Path, help="Path to run.json generated by eval.")
    summarize_parser.add_argument("scores_csv", type=Path, help="Path to scores.csv with manual scores filled in.")
    summarize_parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Optional path to write markdown summary.",
    )
    summarize_parser.add_argument(
        "--min-good-score",
        type=int,
        default=4,
        help="Minimum score treated as high quality (default: 4).",
    )
    summarize_parser.add_argument(
        "--pass-threshold",
        type=float,
        default=0.8,
        help="Minimum ratio of high-quality photos among scored photos (default: 0.8).",
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.command == "generate":
        run_json_path, report_md_path, scores_csv_path = asyncio.run(
            generate_artifacts(
                photos_dir=args.photos_dir,
                output_dir=args.output_dir,
                variation_seed=args.variation_seed,
            )
        )
        print(f"Generated: {run_json_path}")
        print(f"Generated: {report_md_path}")
        print(f"Generated: {scores_csv_path}")
        return 0

    run = EvalRun.model_validate_json(args.run_json.read_text(encoding="utf-8"))
    scores = load_scores(args.scores_csv)
    metrics = compute_gate_metrics(
        run=run,
        scores=scores,
        min_good_score=args.min_good_score,
        pass_threshold=args.pass_threshold,
    )
    summary = build_summary_report(run, metrics)
    print(summary)

    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(summary, encoding="utf-8")
        print(f"Generated: {args.output_md}")

    return 0 if metrics.passed else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
