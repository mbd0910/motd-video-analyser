"""
Integration tests for edge case validation (Task 011b-2).

Tests that intro and MOTD 2 interlude frames have no false positive
team detections, ensuring OCR pipeline correctly rejects non-match content.
"""

import json
from pathlib import Path


def load_ocr_results(episode_id):
    """Load OCR results from cache."""
    cache_dir = Path("data/cache") / episode_id
    ocr_results_path = cache_dir / "ocr_results.json"

    with open(ocr_results_path) as f:
        data = json.load(f)

    return data["ocr_results"]


def test_intro_has_no_detections():
    """
    Test that intro sequence (0:00-0:50) has no team detections.

    Intro frames should not trigger OCR detections as they contain
    titles, graphics, and presenter but no match content.
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    # Filter detections in intro range (0-50 seconds)
    intro_detections = [r for r in ocr_results if r["start_seconds"] < 50]

    assert len(intro_detections) == 0, \
        f"Found {len(intro_detections)} detections in intro (expected 0):\n" + \
        "\n".join([f"  - {r['frame_path']} at {r['start_time']}" for r in intro_detections[:5]])


def test_motd2_interlude_has_no_detections():
    """
    Test that MOTD 2 interlude (52:01-52:47) has no team detections.

    The MOTD 2 interlude is a transition segment between MOTD 1 and
    MOTD 2 coverage, containing graphics but no match content.
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    # MOTD 2 interlude range: 52:01 to 52:47 (3121-3167 seconds)
    interlude_start = 52 * 60 + 1  # 3121 seconds
    interlude_end = 52 * 60 + 47    # 3167 seconds

    # Filter detections in interlude range
    interlude_detections = [r for r in ocr_results
                            if interlude_start <= r["start_seconds"] <= interlude_end]

    assert len(interlude_detections) == 0, \
        f"Found {len(interlude_detections)} detections in MOTD 2 interlude (expected 0):\n" + \
        "\n".join([f"  - {r['frame_path']} at {r['start_time']}" for r in interlude_detections[:5]])


def test_edge_case_coverage():
    """
    Summary test: verify overall edge case detection cleanliness.

    Reports counts for intro, interlude, and provides confidence that
    the OCR pipeline is not generating false positives in non-match content.
    """
    ocr_results = load_ocr_results("motd_2025-26_2025-11-01")

    # Count detections in each edge case region
    intro_count = sum(1 for r in ocr_results if r["start_seconds"] < 50)

    interlude_start = 52 * 60 + 1
    interlude_end = 52 * 60 + 47
    interlude_count = sum(1 for r in ocr_results
                          if interlude_start <= r["start_seconds"] <= interlude_end)

    # Both should be 0
    total_edge_case_detections = intro_count + interlude_count

    assert total_edge_case_detections == 0, \
        f"Edge case detections found: {total_edge_case_detections}\n" \
        f"  - Intro (0:00-0:50): {intro_count}\n" \
        f"  - MOTD 2 interlude (52:01-52:47): {interlude_count}"
