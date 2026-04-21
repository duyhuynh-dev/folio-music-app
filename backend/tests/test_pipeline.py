import pytest

from pipeline.fetch import TrackCandidate
from pipeline.rank import rank_and_explain
from pipeline.scene import Scene


def test_rank_fallback_returns_up_to_four_tracks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    scene = Scene(
        setting="mountain lake",
        time_of_day="golden hour",
        weather="clear",
        energy="quiet",
        mood=["contemplative"],
        palette="warm",
        human_presence="solitary",
        movement="slow",
        cinematic_feel=8,
        season_feel="autumn",
    )
    candidates = [
        TrackCandidate(id=f"id_{i}", name=f"Track {i}", artist="Artist", source="apple_music")
        for i in range(6)
    ]

    ranked = rank_and_explain(scene, candidates, variation_seed=1)
    assert len(ranked) <= 4
    assert all(track.reason for track in ranked)


def test_rank_fallback_penalizes_weather_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    scene = Scene(
        setting="city skyline bridge",
        time_of_day="night",
        weather="clear",
        energy="quiet",
        mood=["melancholic"],
        palette="cool",
        human_presence="none",
        movement="slow",
        cinematic_feel=8,
        season_feel="autumn",
    )
    candidates = [
        TrackCandidate(
            id="rainy",
            name="Dramatic Drizzling Rain Soundtrack",
            artist="Artist Rain",
            source="apple_music",
        ),
        TrackCandidate(
            id="night1",
            name="Midnight Skyline",
            artist="Artist Night",
            source="apple_music",
        ),
        TrackCandidate(
            id="night2",
            name="Neon Bridge Reflections",
            artist="Artist City",
            source="apple_music",
        ),
    ]

    ranked = rank_and_explain(scene, candidates, variation_seed=0)
    assert len(ranked) == 3
    assert ranked[0].id != "rainy"
    assert ranked[1].id != "rainy"
