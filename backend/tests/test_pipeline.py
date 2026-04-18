from pipeline.fetch import TrackCandidate
from pipeline.rank import rank_and_explain
from pipeline.scene import Scene


def test_rank_fallback_returns_up_to_four_tracks() -> None:
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
