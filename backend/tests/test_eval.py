from __future__ import annotations

import csv
from pathlib import Path

import pytest

from eval import (
    EvalPhotoResult,
    EvalRun,
    compute_gate_metrics,
    find_photo_paths,
    load_scores,
)


def test_find_photo_paths_filters_and_sorts(tmp_path: Path) -> None:
    (tmp_path / "b.png").write_bytes(b"img")
    (tmp_path / "a.jpg").write_bytes(b"img")
    (tmp_path / "ignore.txt").write_text("nope", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.webp").write_bytes(b"img")

    found = find_photo_paths(tmp_path)
    assert [path.relative_to(tmp_path).as_posix() for path in found] == [
        "a.jpg",
        "b.png",
        "nested/c.webp",
    ]


def test_find_photo_paths_raises_when_empty(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="No photos found"):
        find_photo_paths(tmp_path)


def test_load_scores_parses_valid_rows(tmp_path: Path) -> None:
    scores_path = tmp_path / "scores.csv"
    with scores_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["photo_name", "score_1_to_5", "notes"])
        writer.writerow(["a.jpg", "5", "great"])
        writer.writerow(["b.jpg", "", "skip"])
        writer.writerow(["c.jpg", "3", "ok"])

    assert load_scores(scores_path) == {"a.jpg": 5, "c.jpg": 3}


def test_load_scores_rejects_invalid_score(tmp_path: Path) -> None:
    scores_path = tmp_path / "scores.csv"
    with scores_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["photo_name", "score_1_to_5", "notes"])
        writer.writerow(["a.jpg", "10", "bad"])

    with pytest.raises(RuntimeError, match="must be between 1 and 5"):
        load_scores(scores_path)


def test_compute_gate_metrics_from_scores() -> None:
    run = EvalRun(
        generated_at_utc="2026-04-13T00:00:00+00:00",
        photos_dir="/tmp/photos",
        total_photos=3,
        variation_seed=0,
        results=[
            EvalPhotoResult(photo_name="a.jpg", relative_path="a.jpg"),
            EvalPhotoResult(photo_name="b.jpg", relative_path="b.jpg"),
            EvalPhotoResult(photo_name="c.jpg", relative_path="c.jpg", error="pipeline timeout"),
        ],
    )
    scores = {"a.jpg": 4, "b.jpg": 5}
    metrics = compute_gate_metrics(run, scores=scores, min_good_score=4, pass_threshold=0.8)

    assert metrics.scored_photos == 2
    assert metrics.unscored_photos == 0
    assert metrics.high_quality_photos == 2
    assert metrics.average_score == 4.5
    assert metrics.quality_ratio == 1.0
    assert metrics.passed is True


def test_compute_gate_metrics_fails_below_threshold() -> None:
    run = EvalRun(
        generated_at_utc="2026-04-13T00:00:00+00:00",
        photos_dir="/tmp/photos",
        total_photos=2,
        variation_seed=0,
        results=[
            EvalPhotoResult(photo_name="a.jpg", relative_path="a.jpg"),
            EvalPhotoResult(photo_name="b.jpg", relative_path="b.jpg"),
        ],
    )
    scores = {"a.jpg": 3, "b.jpg": 4}
    metrics = compute_gate_metrics(run, scores=scores, min_good_score=4, pass_threshold=0.8)

    assert metrics.high_quality_photos == 1
    assert metrics.quality_ratio == 0.5
    assert metrics.passed is False
