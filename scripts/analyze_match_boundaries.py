#!/usr/bin/env python3
"""
Deep dive analysis of match boundaries and segment patterns.
"""

import json
from pathlib import Path
from collections import defaultdict


# Ground truth from docs/motd_visual_patterns.md
MATCHES = [
    {
        "order": 1,
        "teams": ["Liverpool", "Aston Villa"],
        "intro_start": 50,  # 00:00:50
        "highlights_start": 71,  # 00:01:11 (team walkouts)
        "first_half_start": 111,  # 00:01:51
        "second_half_start": 378,  # 00:06:18
        "interviews_start": 611,  # 00:10:11
        "analysis_start": 664,  # 00:11:04
        "end": 865,  # 00:14:25 (next match starts)
    },
    {
        "order": 2,
        "teams": ["Burnley", "Arsenal"],
        "intro_start": 865,  # 00:14:25
        "highlights_start": 876,  # 00:14:36
        "first_half_start": 911,  # 00:15:11
        "interviews_start": 1329,  # 00:22:09
        "analysis_start": 1377,  # 00:22:57
        "end": 1587,  # 00:26:27
    },
    {
        "order": 3,
        "teams": ["Forest", "Manchester United"],
        "intro_start": 1587,
        "highlights_start": 1598,
        "interviews_start": 2125,
        "analysis_start": 2199,
        "end": 2509,
    },
]


def load_data():
    """Load cached data."""
    cache_dir = Path("data/cache/motd_2025-26_2025-11-01")

    with open(cache_dir / "scenes.json") as f:
        scenes_data = json.load(f)

    with open(cache_dir / "ocr_results.json") as f:
        ocr_data = json.load(f)

    with open(cache_dir / "transcript.json") as f:
        transcript = json.load(f)

    return scenes_data["scenes"], ocr_data["ocr_results"], transcript


def find_scenes_in_range(scenes, start_sec, end_sec):
    """Find all scenes within a time range."""
    return [
        s for s in scenes
        if s["start_seconds"] >= start_sec and s["end_seconds"] <= end_sec
    ]


def find_scene_at_time(scenes, target_sec):
    """Find scene at specific timestamp."""
    for s in scenes:
        if s["start_seconds"] <= target_sec <= s["end_seconds"]:
            return s
    # Find nearest
    nearest = min(scenes, key=lambda s: abs(s["start_seconds"] - target_sec))
    return nearest


def analyze_match_segments(match, scenes, ocr_by_scene, scene_transcript):
    """Analyze segments for a single match."""
    print(f"\n{'='*70}")
    print(f"MATCH {match['order']}: {' vs '.join(match['teams'])}")
    print(f"{'='*70}")

    # Studio Intro
    print(f"\n--- Studio Intro ({match['intro_start']}s) ---")
    intro_scene = find_scene_at_time(scenes, match['intro_start'])
    print(f"Scene {intro_scene['scene_id']}: {intro_scene['start_time']} → {intro_scene['end_time']} ({intro_scene['duration']:.1f}s)")
    if intro_scene['scene_id'] in scene_transcript:
        segments = scene_transcript[intro_scene['scene_id']]
        for seg in segments[:2]:  # First couple segments
            print(f"  \"{seg['text'][:80]}...\"")

    # Highlights Start
    if "highlights_start" in match:
        print(f"\n--- Highlights Start ({match['highlights_start']}s) ---")
        hl_scene = find_scene_at_time(scenes, match['highlights_start'])
        print(f"Scene {hl_scene['scene_id']}: {hl_scene['start_time']} → {hl_scene['end_time']} ({hl_scene['duration']:.1f}s)")

    # First OCR detection
    print(f"\n--- First OCR Detection ---")
    if "first_half_start" in match:
        first_half_start = match["first_half_start"]
        # Look for OCR in next ~60 seconds
        ocr_scenes = []
        for scene_id in sorted(ocr_by_scene.keys()):
            scene = next((s for s in scenes if s["scene_id"] == scene_id), None)
            if scene and first_half_start <= scene["start_seconds"] <= first_half_start + 60:
                ocr_scenes.append((scene_id, scene["start_seconds"]))

        if ocr_scenes:
            first_ocr_id, first_ocr_time = ocr_scenes[0]
            print(f"First OCR: Scene {first_ocr_id} at {first_ocr_time:.1f}s (offset: +{first_ocr_time - first_half_start:.1f}s from highlights)")
            print(f"Teams detected: {ocr_by_scene[first_ocr_id].get('validated_teams', [])}")
            print(f"Fixture: {ocr_by_scene[first_ocr_id].get('matched_fixture')}")
        else:
            print("No OCR detected in first 60 seconds of highlights")

    # Interviews
    if "interviews_start" in match:
        print(f"\n--- Interviews Start ({match['interviews_start']}s) ---")
        int_scene = find_scene_at_time(scenes, match['interviews_start'])
        print(f"Scene {int_scene['scene_id']}: {int_scene['start_time']} → {int_scene['end_time']} ({int_scene['duration']:.1f}s)")
        if int_scene['scene_id'] in scene_transcript:
            segments = scene_transcript[int_scene['scene_id']]
            for seg in segments[:2]:
                print(f"  \"{seg['text'][:80]}...\"")

    # Studio Analysis
    if "analysis_start" in match:
        print(f"\n--- Studio Analysis Start ({match['analysis_start']}s) ---")
        analysis_scene = find_scene_at_time(scenes, match['analysis_start'])
        print(f"Scene {analysis_scene['scene_id']}: {analysis_scene['start_time']} → {analysis_scene['end_time']} ({analysis_scene['duration']:.1f}s)")
        if analysis_scene['scene_id'] in scene_transcript:
            segments = scene_transcript[analysis_scene['scene_id']]
            for seg in segments[:3]:
                print(f"  \"{seg['text'][:80]}...\"")


def main():
    """Analyze match boundaries."""
    print("Loading data...")
    scenes, ocr_results, transcript = load_data()

    # Create lookups
    ocr_by_scene = {ocr["scene_id"]: ocr for ocr in ocr_results}

    scene_transcript = defaultdict(list)
    for segment in transcript["segments"]:
        for scene in scenes:
            if scene["start_seconds"] <= segment["start"] <= scene["end_seconds"]:
                scene_transcript[scene["scene_id"]].append(segment)
                break

    # Analyze each match
    for match in MATCHES:
        analyze_match_segments(match, scenes, ocr_by_scene, scene_transcript)

    # Overall patterns
    print(f"\n\n{'='*70}")
    print("OVERALL PATTERNS")
    print(f"{'='*70}")

    # Count OCR scenes per fixture
    fixture_ocr_counts = defaultdict(int)
    for ocr in ocr_results:
        if ocr.get("matched_fixture"):
            fixture_ocr_counts[ocr["matched_fixture"]] += 1

    print("\nOCR Scenes per Fixture:")
    for fixture, count in sorted(fixture_ocr_counts.items()):
        print(f"  {fixture}: {count} scenes")


if __name__ == "__main__":
    main()
