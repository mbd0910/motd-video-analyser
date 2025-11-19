"""Tests for sentence extraction from transcript segments."""

import pytest
import json
from pathlib import Path

from motd.analysis.running_order_detector import RunningOrderDetector
from motd.analysis.venue_matcher import VenueMatcher


@pytest.fixture
def detector():
    """Create minimal RunningOrderDetector instance for testing sentence extraction."""
    # Load minimal dependencies
    teams_path = Path("data/teams/premier_league_2025_26.json")
    with open(teams_path) as f:
        data = json.load(f)
        teams_data = data["teams"]

    fixtures_path = Path("data/fixtures/premier_league_2025_26.json")
    with open(fixtures_path) as f:
        data = json.load(f)
        fixtures = data["fixtures"]

    venue_matcher = VenueMatcher("data/venues/premier_league_2025_26.json")

    return RunningOrderDetector(
        ocr_results=[],  # Not needed for sentence extraction
        transcript={"segments": []},  # Not needed for sentence extraction
        teams_data=teams_data,
        fixtures=fixtures,
        venue_matcher=venue_matcher,
    )


def test_multi_segment_sentence(detector):
    """Test combining segments that form one sentence (Match 1 example)."""
    segments = [
        {"start": 61.11, "text": "It was six defeats in seven in all competitions"},
        {"start": 64.63, "text": "for champions Liverpool."},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 61.11
    assert (
        sentences[0]["text"]
        == "It was six defeats in seven in all competitions for champions Liverpool."
    )


def test_single_segment_sentence(detector):
    """Test single segment that is a complete sentence."""
    segments = [
        {
            "start": 66.05,
            "text": "Aston Villa had just won their last four in the league.",
        }
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 66.05
    assert (
        sentences[0]["text"]
        == "Aston Villa had just won their last four in the league."
    )


def test_multiple_complete_sentences(detector):
    """Test multiple segments, each a complete sentence."""
    segments = [
        {
            "start": 51.25,
            "text": "Seven games, plenty of goals and a couple of horror shows.",
        },
        {"start": 54.63, "text": "Alan Shearer and Ashley Williams join us."},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 2
    assert sentences[0]["start"] == 51.25
    assert (
        sentences[0]["text"]
        == "Seven games, plenty of goals and a couple of horror shows."
    )
    assert sentences[1]["start"] == 54.63
    assert sentences[1]["text"] == "Alan Shearer and Ashley Williams join us."


def test_incomplete_sentence_no_punctuation(detector):
    """Test segment without sentence-ending punctuation."""
    segments = [{"start": 72.47, "text": "Only once in the last 70 years"}]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 72.47
    assert sentences[0]["text"] == "Only once in the last 70 years"


def test_empty_segments(detector):
    """Test handling of empty segments."""
    segments = [
        {"start": 10.0, "text": ""},
        {"start": 15.0, "text": "   "},
        {"start": 20.0, "text": "This is a sentence."},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 20.0
    assert sentences[0]["text"] == "This is a sentence."


def test_sentence_with_question_mark(detector):
    """Test sentence ending with question mark."""
    segments = [
        {"start": 30.0, "text": "Is this"},
        {"start": 32.0, "text": "a question?"},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 30.0
    assert sentences[0]["text"] == "Is this a question?"


def test_sentence_with_exclamation(detector):
    """Test sentence ending with exclamation mark."""
    segments = [
        {"start": 40.0, "text": "What a goal!"},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 40.0
    assert sentences[0]["text"] == "What a goal!"


def test_match_2_intro_sentence(detector):
    """Test Match 2 intro sentence (single segment)."""
    segments = [
        {
            "start": 866.30,
            "text": "Leaders, Arsenal didn't concede a goal in October,",
        },
        {"start": 869.04, "text": "winning six matches in all competitions."},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    assert len(sentences) == 1
    assert sentences[0]["start"] == 866.30
    assert (
        sentences[0]["text"]
        == "Leaders, Arsenal didn't concede a goal in October, winning six matches in all competitions."
    )


def test_ok_transition_followed_by_sentence(detector):
    """Test 'OK.' as separate sentence followed by main sentence (Match 4)."""
    segments = [
        {"start": 2506.58, "text": "but once a corner's given, defend it better."},
        {"start": 2509.06, "text": "OK."},
        {
            "start": 2509.50,
            "text": "bottom of the table, Wolves were hunting a first win",
        },
        {"start": 2512.66, "text": "of the season at Fulham, who'd lost their last four."},
    ]

    sentences = detector._extract_sentences_from_segments(segments)

    # Should get 3 sentences:
    # 1. "...defend it better."
    # 2. "OK."
    # 3. "bottom of the table... last four."
    assert len(sentences) == 3
    assert sentences[0]["text"].endswith("defend it better.")
    assert sentences[1]["start"] == 2509.06
    assert sentences[1]["text"] == "OK."
    assert sentences[2]["start"] == 2509.50
    assert "Wolves were hunting" in sentences[2]["text"]
