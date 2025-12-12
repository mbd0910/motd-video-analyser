"""Tests for PromptBuilder."""

import json
import pytest
from pathlib import Path

from motd.llm.prompt_builder import PromptBuilder, Fixture, BuiltPrompt


class TestFixture:
    """Tests for Fixture dataclass."""

    def test_fixture_creation(self):
        """Test basic fixture creation."""
        fix = Fixture(
            match_id="2025-11-22-liverpool-forest",
            date="2025-11-22",
            home_team="Liverpool",
            away_team="Nottingham Forest",
            venue="Anfield",
            kickoff="15:00",
            final_score={"home": 0, "away": 3},
        )

        assert fix.home_team == "Liverpool"
        assert fix.away_team == "Nottingham Forest"
        assert fix.final_score["home"] == 0


class TestPromptBuilderFixtures:
    """Tests for fixture loading."""

    def test_load_fixtures_no_manifest(self, tmp_path: Path):
        """Test handling when manifest doesn't exist."""
        builder = PromptBuilder(
            tmp_path,
            manifest_path=tmp_path / "nonexistent.json",
        )

        fixtures = builder.load_fixtures_for_episode()
        assert fixtures == []

    def test_load_fixtures_no_episode(self, tmp_path: Path):
        """Test handling when episode not in manifest."""
        # Create manifest without the episode
        manifest = {"season": "2025-26", "episodes": []}
        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        builder = PromptBuilder(
            tmp_path / "nonexistent_episode",
            manifest_path=manifest_path,
        )

        fixtures = builder.load_fixtures_for_episode()
        assert fixtures == []


class TestPromptBuilderSections:
    """Tests for prompt section building."""

    def test_build_header(self, tmp_path: Path):
        """Test header section building."""
        builder = PromptBuilder(tmp_path / "test_episode")
        episode = {"broadcast_date": "2025-11-22"}

        header = builder._build_header(episode)

        assert "2025-11-22" in header
        assert "BBC One" in header
        assert "test_episode" in header

    def test_build_header_no_episode(self, tmp_path: Path):
        """Test header with no episode data."""
        builder = PromptBuilder(tmp_path / "test_episode")

        header = builder._build_header(None)

        assert "Unknown" in header

    def test_build_fixtures_table_empty(self, tmp_path: Path):
        """Test fixtures table with no fixtures."""
        builder = PromptBuilder(tmp_path)

        table = builder._build_fixtures_table([])

        assert "No fixtures data available" in table

    def test_build_fixtures_table_with_data(self, tmp_path: Path):
        """Test fixtures table with fixture data."""
        builder = PromptBuilder(tmp_path)
        fixtures = [
            Fixture(
                match_id="test-1",
                date="2025-11-22",
                home_team="Liverpool",
                away_team="Forest",
                venue="Anfield",
                final_score={"home": 0, "away": 3},
            ),
        ]

        table = builder._build_fixtures_table(fixtures)

        assert "Liverpool" in table
        assert "Forest" in table
        assert "Anfield" in table
        assert "0-3" in table

    def test_build_task_description(self, tmp_path: Path):
        """Test task description contains key instructions."""
        builder = PromptBuilder(tmp_path)

        desc = builder._build_task_description()

        # Check key instructions are present
        assert "editorial choice" in desc
        assert "studio_intro" in desc
        assert "lineups" in desc
        assert "highlights" in desc
        assert "commentator credit" in desc.lower()

    def test_build_output_schema(self, tmp_path: Path):
        """Test output schema is valid JSON."""
        builder = PromptBuilder(tmp_path)

        schema = builder._build_output_schema()

        # Should contain JSON code block
        assert "```json" in schema
        assert "episode" in schema
        assert "matches" in schema


class TestPromptBuilderIntegration:
    """Integration tests for full prompt building."""

    def test_build_prompt_minimal(self, tmp_path: Path):
        """Test building prompt with minimal data."""
        # Create minimal transcript
        transcript_data = {
            "duration": 300.0,
            "segments": [
                {"start": 0.0, "text": "Welcome to Match of the Day."},
                {"start": 10.0, "text": "First match starts now."},
            ],
        }
        transcript_path = tmp_path / "transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(transcript_data, f)

        # Create minimal manifest
        manifest = {
            "season": "2025-26",
            "episodes": [
                {
                    "episode_id": tmp_path.name,
                    "broadcast_date": "2025-11-22",
                    "expected_matches": [],
                }
            ],
        }
        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        builder = PromptBuilder(
            tmp_path,
            include_hints=False,
            manifest_path=manifest_path,
            fixtures_path=tmp_path / "fixtures.json",
        )

        result = builder.build()

        assert isinstance(result, BuiltPrompt)
        assert "Welcome to Match of the Day" in result.content
        assert result.transcript_stats.segment_count == 2
        assert result.has_ocr_hints is False

    def test_build_prompt_with_ocr_hints(self, tmp_path: Path):
        """Test building prompt with OCR hints included."""
        # Create transcript
        transcript_data = {
            "duration": 300.0,
            "segments": [{"start": 0.0, "text": "Test segment."}],
        }
        with open(tmp_path / "transcript.json", "w") as f:
            json.dump(transcript_data, f)

        # Create OCR results
        ocr_data = {
            "expected_fixtures": [
                {"match_id": "test-match", "home_team": "Team A", "away_team": "Team B"}
            ],
            "ocr_results": [
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 100.0,
                    "validated_teams": ["Team A", "Team B"],
                    "matched_fixture": "test-match",
                }
            ],
        }
        with open(tmp_path / "ocr_results.json", "w") as f:
            json.dump(ocr_data, f)

        # Create manifest
        manifest = {
            "season": "2025-26",
            "episodes": [
                {
                    "episode_id": tmp_path.name,
                    "broadcast_date": "2025-11-22",
                    "expected_matches": [],
                }
            ],
        }
        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        builder = PromptBuilder(
            tmp_path,
            include_hints=True,
            manifest_path=manifest_path,
            fixtures_path=tmp_path / "fixtures.json",
        )

        result = builder.build()

        assert result.has_ocr_hints is True
        assert "Image Analysis Hints" in result.content
        assert "Full-Time Graphics" in result.content

    def test_build_prompt_no_hints_when_disabled(self, tmp_path: Path):
        """Test that hints are excluded when disabled."""
        # Create transcript
        transcript_data = {
            "duration": 300.0,
            "segments": [{"start": 0.0, "text": "Test."}],
        }
        with open(tmp_path / "transcript.json", "w") as f:
            json.dump(transcript_data, f)

        # Create OCR results (would produce hints if enabled)
        ocr_data = {
            "expected_fixtures": [],
            "ocr_results": [
                {
                    "ocr_source": "ft_score",
                    "start_seconds": 100.0,
                    "validated_teams": ["A", "B"],
                }
            ],
        }
        with open(tmp_path / "ocr_results.json", "w") as f:
            json.dump(ocr_data, f)

        builder = PromptBuilder(tmp_path, include_hints=False)

        result = builder.build()

        assert result.has_ocr_hints is False
        # The header "## Image Analysis Hints (Advisory)" should not appear
        # Note: "Image Analysis Hints" appears in task description as guidance
        assert "## Image Analysis Hints (Advisory)" not in result.content
        assert "Full-Time Graphics Detected" not in result.content

    def test_estimated_tokens(self, tmp_path: Path):
        """Test token estimation is reasonable."""
        # Create transcript with known content
        transcript_data = {
            "duration": 300.0,
            "segments": [{"start": 0.0, "text": "A" * 1000}],  # 1000 chars
        }
        with open(tmp_path / "transcript.json", "w") as f:
            json.dump(transcript_data, f)

        builder = PromptBuilder(tmp_path, include_hints=False)
        result = builder.build()

        # Token estimate should be roughly chars / 4
        # Content has headers + 1000 char transcript
        assert result.estimated_tokens > 250  # At least 1000/4
        assert result.estimated_tokens < 10000  # Not unreasonably high
