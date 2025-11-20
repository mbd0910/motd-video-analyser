"""
Unit tests for Pydantic models.

Tests serialization, deserialization, and validation of pipeline data models.
"""

import pytest
from pydantic import ValidationError

from motd.pipeline.models import Scene, TeamMatch, OCRResult, ProcessedScene


class TestSceneModel:
    """Tests for Scene model."""

    def test_valid_scene(self):
        """Test creating a valid scene."""
        scene = Scene(
            scene_number=1,
            start_time="00:00:15",
            start_seconds=15.0,
            end_seconds=18.5,
            duration=3.5,
            frames=["frame_001.jpg", "frame_002.jpg"],
            key_frame_path="frame_001.jpg"
        )

        assert scene.scene_number == 1
        assert scene.start_seconds == 15.0
        assert scene.end_seconds == 18.5
        assert len(scene.frames) == 2

    def test_scene_serialization(self):
        """Test Scene serialization to dict."""
        scene = Scene(
            scene_number=1,
            start_time="00:00:15",
            start_seconds=15.0,
            end_seconds=18.5,
            duration=3.5
        )

        scene_dict = scene.model_dump()
        assert scene_dict['scene_number'] == 1
        assert scene_dict['frames'] == []  # Default value

    def test_scene_deserialization(self):
        """Test Scene deserialization from dict."""
        data = {
            'scene_number': 42,
            'start_time': '00:10:07',
            'start_seconds': 607.3,
            'end_seconds': 610.8,
            'duration': 3.5,
            'frames': ['frame_0329.jpg']
        }

        scene = Scene(**data)
        assert scene.scene_number == 42
        assert scene.start_seconds == 607.3

    def test_scene_validation_end_before_start(self):
        """Test that end_seconds must be greater than start_seconds."""
        with pytest.raises(ValidationError) as exc_info:
            Scene(
                scene_number=1,
                start_time="00:00:15",
                start_seconds=18.5,
                end_seconds=15.0,  # Before start!
                duration=3.5
            )

        assert 'end_seconds must be greater than start_seconds' in str(exc_info.value)

    def test_scene_negative_duration(self):
        """Test that duration cannot be negative."""
        with pytest.raises(ValidationError):
            Scene(
                scene_number=1,
                start_time="00:00:15",
                start_seconds=15.0,
                end_seconds=18.5,
                duration=-3.5  # Negative!
            )


class TestTeamMatchModel:
    """Tests for TeamMatch model."""

    def test_valid_team_match_ocr(self):
        """Test creating a valid TeamMatch from OCR."""
        match = TeamMatch(
            team="Liverpool",
            confidence=0.95,
            matched_text="Liverpoo",
            source="ocr"
        )

        assert match.team == "Liverpool"
        assert match.confidence == 0.95
        assert match.source == "ocr"

    def test_valid_team_match_inferred(self):
        """Test creating a valid TeamMatch from fixture inference."""
        match = TeamMatch(
            team="Aston Villa",
            confidence=0.75,
            matched_text="",
            source="inferred_from_fixture"
        )

        assert match.team == "Aston Villa"
        assert match.source == "inferred_from_fixture"

    def test_team_match_invalid_source(self):
        """Test that source must be 'ocr' or 'inferred_from_fixture'."""
        with pytest.raises(ValidationError) as exc_info:
            TeamMatch(
                team="Liverpool",
                confidence=0.95,
                matched_text="Liverpool",
                source="invalid_source"
            )

        assert "source must be one of" in str(exc_info.value)

    def test_team_match_confidence_bounds(self):
        """Test that confidence must be between 0.0 and 1.0."""
        # Too high
        with pytest.raises(ValidationError):
            TeamMatch(
                team="Liverpool",
                confidence=1.5,  # > 1.0
                matched_text="Liverpool",
                source="ocr"
            )

        # Negative
        with pytest.raises(ValidationError):
            TeamMatch(
                team="Liverpool",
                confidence=-0.1,  # < 0.0
                matched_text="Liverpool",
                source="ocr"
            )


class TestOCRResultModel:
    """Tests for OCRResult model."""

    def test_valid_ocr_result(self):
        """Test creating a valid OCR result."""
        result = OCRResult(
            primary_source="ft_score",
            results=[
                {"text": "Liverpool", "confidence": 0.95},
                {"text": "2", "confidence": 0.98}
            ],
            confidence=0.965
        )

        assert result.primary_source == "ft_score"
        assert len(result.results) == 2
        assert result.confidence == 0.965

    def test_ocr_result_invalid_source(self):
        """Test that primary_source must be valid OCR region."""
        with pytest.raises(ValidationError) as exc_info:
            OCRResult(
                primary_source="invalid_region",
                results=[],
                confidence=0.9
            )

        assert "primary_source must be one of" in str(exc_info.value)

    def test_ocr_result_serialization(self):
        """Test OCRResult serialization with nested dicts."""
        result = OCRResult(
            primary_source="scoreboard",
            results=[{"text": "Arsenal", "confidence": 0.92}],
            confidence=0.92
        )

        result_dict = result.model_dump()
        assert result_dict['primary_source'] == "scoreboard"
        assert len(result_dict['results']) == 1


class TestProcessedSceneModel:
    """Tests for ProcessedScene model."""

    def test_valid_processed_scene(self):
        """Test creating a valid processed scene."""
        scene = ProcessedScene(
            scene_number=42,
            start_time="00:10:07",
            start_seconds=607.3,
            frame_path="data/cache/frames/frame_0329.jpg",
            ocr_source="ft_score",
            team1="Liverpool",
            team2="Aston Villa",
            match_confidence=0.88,
            fixture_id="2025-11-01-liverpool-astonvilla",
            home_team="Liverpool",
            away_team="Aston Villa"
        )

        assert scene.team1 == "Liverpool"
        assert scene.team2 == "Aston Villa"
        assert scene.fixture_id == "2025-11-01-liverpool-astonvilla"
        assert scene.home_team == "Liverpool"
        assert scene.away_team == "Aston Villa"

    def test_processed_scene_without_fixture(self):
        """Test processed scene without fixture ID (fixture-less detection)."""
        scene = ProcessedScene(
            scene_number=42,
            start_time="00:10:07",
            start_seconds=607.3,
            frame_path="frame.jpg",
            ocr_source="scoreboard",
            team1="Liverpool",
            team2="Manchester United",
            match_confidence=0.92
            # No fixture_id, home_team, away_team - all optional
        )

        assert scene.fixture_id is None
        assert scene.home_team is None
        assert scene.away_team is None

    def test_processed_scene_invalid_ocr_source(self):
        """Test that ocr_source must be valid."""
        with pytest.raises(ValidationError) as exc_info:
            ProcessedScene(
                scene_number=1,
                start_time="00:00:15",
                start_seconds=15.0,
                frame_path="frame.jpg",
                ocr_source="invalid_source",
                team1="Liverpool",
                team2="Arsenal",
                match_confidence=0.9
            )

        assert "ocr_source must be one of" in str(exc_info.value)

    def test_processed_scene_json_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = ProcessedScene(
            scene_number=42,
            start_time="00:10:07",
            start_seconds=607.3,
            frame_path="frame.jpg",
            ocr_source="ft_score",
            team1="Liverpool",
            team2="Aston Villa",
            match_confidence=0.88,
            fixture_id="2025-11-01-liverpool-astonvilla"
        )

        # Serialize to dict
        scene_dict = original.model_dump()

        # Deserialize from dict
        restored = ProcessedScene(**scene_dict)

        assert restored == original
        assert restored.team1 == "Liverpool"
        assert restored.fixture_id == "2025-11-01-liverpool-astonvilla"
