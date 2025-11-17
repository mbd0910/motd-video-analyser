#!/usr/bin/env python3
"""
Task 011a: Analysis Reconnaissance Script

Analyzes cached data (scenes, OCR, transcript) to discover classification patterns
for segment types and validate against ground truth.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import re


# Ground truth from docs/motd_visual_patterns.md (lines 95-102)
GROUND_TRUTH_MATCHES = [
    {"order": 1, "teams": ["Liverpool", "Aston Villa"], "start_seconds": 50},
    {"order": 2, "teams": ["Burnley", "Arsenal"], "start_seconds": 865},
    {"order": 3, "teams": ["Forest", "Manchester United"], "start_seconds": 1587},
    {"order": 4, "teams": ["Fulham", "Wolves"], "start_seconds": 2509},
    {"order": 5, "teams": ["Spurs", "Chelsea"], "start_seconds": 3167},
    {"order": 6, "teams": ["Brighton", "Leeds"], "start_seconds": 3894},
    {"order": 7, "teams": ["Palace", "Brentford"], "start_seconds": 4480},
]


def load_data(cache_dir: Path) -> Tuple[Dict, List, Dict]:
    """Load all cached data files."""
    print("Loading cached data...")

    # Load scenes
    with open(cache_dir / "scenes.json") as f:
        scenes_data = json.load(f)
    scenes = scenes_data["scenes"]
    print(f"  Loaded {len(scenes)} scenes")

    # Load OCR results
    with open(cache_dir / "ocr_results.json") as f:
        ocr_data = json.load(f)
    ocr_results = ocr_data["ocr_results"]
    print(f"  Loaded OCR results for {len(ocr_results)} scenes")

    # Load transcript
    with open(cache_dir / "transcript.json") as f:
        transcript = json.load(f)
    print(f"  Loaded transcript with {len(transcript['segments'])} segments")

    return scenes_data, ocr_results, transcript


def map_ocr_to_scenes(scenes: List[Dict], ocr_results: List[Dict]) -> Dict:
    """Map OCR results back to scenes."""
    ocr_by_scene = {}
    for ocr in ocr_results:
        scene_id = ocr.get("scene_id")
        if scene_id:
            ocr_by_scene[scene_id] = ocr
    return ocr_by_scene


def map_transcript_to_scenes(scenes: List[Dict], transcript_segments: List[Dict]) -> Dict:
    """Map transcript segments to overlapping scenes."""
    scene_transcript = defaultdict(list)

    for segment in transcript_segments:
        seg_start = segment["start"]
        seg_end = segment["end"]

        # Find overlapping scenes
        for scene in scenes:
            scene_start = scene["start_seconds"]
            scene_end = scene["end_seconds"]

            # Check if segment overlaps with scene
            if not (seg_end < scene_start or seg_start > scene_end):
                scene_transcript[scene["scene_id"]].append(segment)

    return scene_transcript


def analyze_ocr_patterns(ocr_by_scene: Dict) -> Dict:
    """Analyze OCR detection patterns."""
    print("\n=== OCR Pattern Analysis ===")

    patterns = {
        "total_ocr_scenes": len(ocr_by_scene),
        "scenes_with_teams": 0,
        "scenes_with_ft_graphic": 0,
        "scenes_with_scoreboards": 0,
        "scenes_with_formations": 0,
        "fixture_matches": set(),
    }

    for scene_id, ocr in ocr_by_scene.items():
        if ocr.get("validated_teams"):
            patterns["scenes_with_teams"] += 1

        if ocr.get("ocr_source") == "ft_graphic":
            patterns["scenes_with_ft_graphic"] += 1
            print(f"  FT Graphic detected: Scene {scene_id}, Teams: {ocr.get('validated_teams', [])}")

        if ocr.get("ocr_source") == "scoreboard":
            patterns["scenes_with_scoreboards"] += 1

        if ocr.get("ocr_source") == "formation":
            patterns["scenes_with_formations"] += 1

        if ocr.get("matched_fixture"):
            patterns["fixture_matches"].add(ocr["matched_fixture"])

    patterns["unique_fixtures"] = len(patterns["fixture_matches"])
    patterns["fixture_list"] = sorted(list(patterns["fixture_matches"]))

    print(f"\nTotal OCR scenes: {patterns['total_ocr_scenes']}")
    print(f"Scenes with teams: {patterns['scenes_with_teams']}")
    print(f"Scenes with FT graphics: {patterns['scenes_with_ft_graphic']}")
    print(f"Scenes with scoreboards: {patterns['scenes_with_scoreboards']}")
    print(f"Scenes with formations: {patterns['scenes_with_formations']}")
    print(f"Unique fixtures matched: {patterns['unique_fixtures']}")
    print(f"Fixtures: {patterns['fixture_list']}")

    return patterns


def analyze_transcript_patterns(scene_transcript: Dict, transcript: Dict) -> Dict:
    """Analyze transcript patterns."""
    print("\n=== Transcript Pattern Analysis ===")

    total_segments = len(transcript["segments"])
    scenes_with_transcript = len(scene_transcript)

    # Count scenes by number of transcript segments
    segments_per_scene = Counter()
    for scene_id, segments in scene_transcript.items():
        segments_per_scene[len(segments)] += 1

    # Find transition keywords
    transition_keywords = ["alright", "right", "moving on", "now", "next", "let's look"]
    scenes_with_transitions = []

    for scene_id, segments in scene_transcript.items():
        for segment in segments:
            text_lower = segment["text"].lower()
            for keyword in transition_keywords:
                if keyword in text_lower:
                    scenes_with_transitions.append({
                        "scene_id": scene_id,
                        "keyword": keyword,
                        "text": segment["text"][:100]
                    })
                    break

    print(f"\nTotal transcript segments: {total_segments}")
    print(f"Scenes with overlapping speech: {scenes_with_transcript}")
    print(f"Scenes with transition keywords: {len(scenes_with_transitions)}")

    if scenes_with_transitions:
        print("\nSample transition keywords found:")
        for item in scenes_with_transitions[:10]:
            print(f"  Scene {item['scene_id']}: '{item['keyword']}' in \"{item['text']}\"")

    return {
        "total_segments": total_segments,
        "scenes_with_transcript": scenes_with_transcript,
        "scenes_with_transitions": len(scenes_with_transitions),
        "transition_examples": scenes_with_transitions[:20]
    }


def analyze_scene_durations(scenes: List[Dict]) -> Dict:
    """Analyze scene duration patterns."""
    print("\n=== Scene Duration Analysis ===")

    durations = [s["duration"] for s in scenes]

    # Categorize by duration
    very_short = [d for d in durations if d < 2.0]  # < 2 seconds
    short = [d for d in durations if 2.0 <= d < 15.0]  # 2-15 seconds
    medium = [d for d in durations if 15.0 <= d < 60.0]  # 15-60 seconds
    long = [d for d in durations if d >= 60.0]  # 60+ seconds

    print(f"\nTotal scenes: {len(scenes)}")
    print(f"Very short (<2s): {len(very_short)}")
    print(f"Short (2-15s): {len(short)}")
    print(f"Medium (15-60s): {len(medium)}")
    print(f"Long (60+s): {len(long)}")

    # Find scenes in the 7-11 second range (potential studio intros)
    intro_range = [s for s in scenes if 7.0 <= s["duration"] <= 11.0]
    print(f"\nScenes in studio intro range (7-11s): {len(intro_range)}")

    return {
        "very_short": len(very_short),
        "short": len(short),
        "medium": len(medium),
        "long": len(long),
        "intro_range_count": len(intro_range),
        "intro_range_scenes": [s["scene_id"] for s in intro_range[:20]]
    }


def validate_against_ground_truth(scenes: List[Dict], ocr_by_scene: Dict) -> Dict:
    """Validate OCR detections against ground truth match timestamps."""
    print("\n=== Ground Truth Validation ===")

    results = []

    for match in GROUND_TRUTH_MATCHES:
        # Find scene at this timestamp
        target_time = match["start_seconds"]
        nearest_scene = None
        min_diff = float('inf')

        for scene in scenes:
            # Check if timestamp falls within scene
            if scene["start_seconds"] <= target_time <= scene["end_seconds"]:
                nearest_scene = scene
                break

            # Otherwise find nearest
            diff = abs(scene["start_seconds"] - target_time)
            if diff < min_diff:
                min_diff = diff
                nearest_scene = scene

        if nearest_scene:
            scene_id = nearest_scene["scene_id"]
            ocr = ocr_by_scene.get(scene_id, {})

            result = {
                "match_order": match["order"],
                "expected_teams": match["teams"],
                "expected_time": target_time,
                "scene_id": scene_id,
                "scene_start": nearest_scene["start_seconds"],
                "time_diff": abs(nearest_scene["start_seconds"] - target_time),
                "ocr_detected": bool(ocr),
                "ocr_teams": ocr.get("validated_teams", []),
                "fixture_match": ocr.get("matched_fixture"),
            }

            results.append(result)

            status = "✓" if ocr.get("validated_teams") else "✗"
            print(f"\nMatch {match['order']}: {' vs '.join(match['teams'])}")
            print(f"  {status} Expected time: {target_time}s, Nearest scene: {scene_id} ({nearest_scene['start_seconds']}s)")
            print(f"  OCR detected: {bool(ocr)}, Teams: {ocr.get('validated_teams', 'None')}")
            print(f"  Fixture: {ocr.get('matched_fixture', 'None')}")

    detected_count = sum(1 for r in results if r["ocr_detected"])
    print(f"\n✓ Matches with OCR detection: {detected_count}/7")

    return {
        "total_matches": 7,
        "detected": detected_count,
        "results": results
    }


def find_ft_graphics(scenes: List[Dict], ocr_by_scene: Dict) -> List[Dict]:
    """Find all FT (Full Time) graphics."""
    print("\n=== FT Graphic Detection ===")

    ft_scenes = []
    for scene in scenes:
        scene_id = scene["scene_id"]
        ocr = ocr_by_scene.get(scene_id, {})

        if ocr.get("ocr_source") == "ft_graphic":
            ft_scenes.append({
                "scene_id": scene_id,
                "start_time": scene["start_time"],
                "start_seconds": scene["start_seconds"],
                "teams": ocr.get("validated_teams", []),
                "fixture": ocr.get("matched_fixture")
            })
            print(f"  Scene {scene_id} ({scene['start_time']}): {ocr.get('validated_teams', [])}")

    print(f"\nTotal FT graphics detected: {len(ft_scenes)}/7 expected")

    return ft_scenes


def main():
    """Run reconnaissance analysis."""
    cache_dir = Path("data/cache/motd_2025-26_2025-11-01")

    # Load data
    scenes_data, ocr_results, transcript = load_data(cache_dir)
    scenes = scenes_data["scenes"]

    # Map data
    print("\nMapping data relationships...")
    ocr_by_scene = map_ocr_to_scenes(scenes, ocr_results)
    scene_transcript = map_transcript_to_scenes(scenes, transcript["segments"])
    print(f"  OCR mapped to {len(ocr_by_scene)} scenes")
    print(f"  Transcript mapped to {len(scene_transcript)} scenes")

    # Analyze patterns
    ocr_patterns = analyze_ocr_patterns(ocr_by_scene)
    transcript_patterns = analyze_transcript_patterns(scene_transcript, transcript)
    duration_patterns = analyze_scene_durations(scenes)

    # Validate
    validation_results = validate_against_ground_truth(scenes, ocr_by_scene)
    ft_graphics = find_ft_graphics(scenes, ocr_by_scene)

    # Summary
    print("\n" + "=" * 60)
    print("RECONNAISSANCE SUMMARY")
    print("=" * 60)
    print(f"\nData Coverage:")
    print(f"  Total scenes: {len(scenes)}")
    print(f"  Scenes with OCR: {len(ocr_by_scene)} ({len(ocr_by_scene)/len(scenes)*100:.1f}%)")
    print(f"  Scenes with transcript: {len(scene_transcript)} ({len(scene_transcript)/len(scenes)*100:.1f}%)")
    print(f"  Scenes with teams: {ocr_patterns['scenes_with_teams']}")
    print(f"  Scenes with FT graphics: {ocr_patterns['scenes_with_ft_graphic']}")
    print(f"  Unique fixtures: {ocr_patterns['unique_fixtures']}")

    print(f"\nGround Truth Validation:")
    print(f"  Matches detected: {validation_results['detected']}/7")
    print(f"  FT graphics found: {len(ft_graphics)}/7")

    print(f"\nSegment Duration Patterns:")
    print(f"  Very short (<2s): {duration_patterns['very_short']}")
    print(f"  Short (2-15s): {duration_patterns['short']}")
    print(f"  Medium (15-60s): {duration_patterns['medium']}")
    print(f"  Long (60+s): {duration_patterns['long']}")
    print(f"  Studio intro range (7-11s): {duration_patterns['intro_range_count']}")

    print(f"\nTranscript Patterns:")
    print(f"  Scenes with transition keywords: {transcript_patterns['scenes_with_transitions']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
