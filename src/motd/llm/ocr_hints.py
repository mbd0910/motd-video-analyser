"""OCR hints extraction for LLM prompts.

Extracts advisory hints from OCR results to help LLMs anchor
their analysis. Includes FT graphics and first scoreboard
appearances.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FTGraphicHint:
    """A detected full-time graphic."""

    timestamp_seconds: float
    home_team: str
    away_team: str
    confidence: float = 1.0

    @property
    def timestamp_formatted(self) -> str:
        """Format timestamp as MM:SS."""
        mins = int(self.timestamp_seconds // 60)
        secs = int(self.timestamp_seconds % 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class ScoreboardHint:
    """A detected scoreboard appearance."""

    timestamp_seconds: float
    home_team: str
    away_team: str
    is_first_appearance: bool = True

    @property
    def timestamp_formatted(self) -> str:
        """Format timestamp as MM:SS."""
        mins = int(self.timestamp_seconds // 60)
        secs = int(self.timestamp_seconds % 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class OCRHints:
    """Collection of OCR-derived hints for LLM analysis."""

    ft_graphics: list[FTGraphicHint] = field(default_factory=list)
    first_scoreboards: list[ScoreboardHint] = field(default_factory=list)

    @property
    def has_hints(self) -> bool:
        """Check if any hints are available."""
        return bool(self.ft_graphics or self.first_scoreboards)


class OCRHintsExtractor:
    """Extracts advisory hints from OCR results.

    Provides FT graphic timestamps and first scoreboard appearances
    to help LLMs anchor their analysis of episode structure.
    """

    def __init__(self, cache_path: Path | str) -> None:
        """Initialise with path to episode cache folder.

        Args:
            cache_path: Path to episode cache folder.
        """
        self.cache_path = Path(cache_path)
        self.ocr_results_path = self.cache_path / "ocr_results.json"

    def load_ocr_results(self) -> dict[str, Any] | None:
        """Load ocr_results.json from cache.

        Returns:
            Parsed OCR results data, or None if file doesn't exist.
        """
        if not self.ocr_results_path.exists():
            logger.warning("OCR results not found: %s", self.ocr_results_path)
            return None

        with open(self.ocr_results_path) as f:
            return json.load(f)

    def extract_ft_graphics(
        self, ocr_results: dict[str, Any], min_confidence: float = 0.7
    ) -> list[FTGraphicHint]:
        """Extract FT graphic timestamps from OCR results.

        Args:
            ocr_results: Parsed OCR results data.
            min_confidence: Minimum confidence threshold for inclusion.

        Returns:
            List of FT graphic hints sorted by timestamp.
        """
        results = ocr_results.get("ocr_results", [])
        ft_hints: list[FTGraphicHint] = []

        for result in results:
            if result.get("ocr_source") != "ft_score":
                continue

            teams = result.get("validated_teams", [])
            if len(teams) < 2:
                continue

            # Get confidence from detected teams
            detected_teams = result.get("detected_teams", [])
            avg_confidence = 1.0
            if detected_teams:
                confidences = [t.get("confidence", 1.0) for t in detected_teams]
                avg_confidence = sum(confidences) / len(confidences)

            if avg_confidence < min_confidence:
                continue

            # Use expected_fixtures to determine home/away order
            fixture_id = result.get("matched_fixture", "")
            home_team, away_team = self._order_teams_by_fixture(
                teams, fixture_id, ocr_results.get("expected_fixtures", [])
            )

            ft_hints.append(
                FTGraphicHint(
                    timestamp_seconds=result.get("start_seconds", 0),
                    home_team=home_team,
                    away_team=away_team,
                    confidence=avg_confidence,
                )
            )

        # Sort by timestamp
        ft_hints.sort(key=lambda h: h.timestamp_seconds)

        logger.info("Extracted %d FT graphic hints", len(ft_hints))
        return ft_hints

    def extract_first_scoreboards(
        self, ocr_results: dict[str, Any]
    ) -> list[ScoreboardHint]:
        """Extract first scoreboard appearance per match.

        Args:
            ocr_results: Parsed OCR results data.

        Returns:
            List of first scoreboard hints sorted by timestamp.
        """
        results = ocr_results.get("ocr_results", [])
        expected_fixtures = ocr_results.get("expected_fixtures", [])

        # Track first scoreboard per fixture
        first_by_fixture: dict[str, ScoreboardHint] = {}

        for result in results:
            if result.get("ocr_source") != "scoreboard":
                continue

            fixture_id = result.get("matched_fixture")
            if not fixture_id:
                continue

            # Skip if we already have an earlier one for this fixture
            if fixture_id in first_by_fixture:
                continue

            teams = result.get("validated_teams", [])
            if len(teams) < 2:
                continue

            home_team, away_team = self._order_teams_by_fixture(
                teams, fixture_id, expected_fixtures
            )

            first_by_fixture[fixture_id] = ScoreboardHint(
                timestamp_seconds=result.get("start_seconds", 0),
                home_team=home_team,
                away_team=away_team,
                is_first_appearance=True,
            )

        # Convert to list and sort by timestamp
        hints = list(first_by_fixture.values())
        hints.sort(key=lambda h: h.timestamp_seconds)

        logger.info("Extracted %d first scoreboard hints", len(hints))
        return hints

    def _order_teams_by_fixture(
        self,
        teams: list[str],
        fixture_id: str,
        expected_fixtures: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """Order teams as home/away based on fixture data.

        Args:
            teams: List of team names (may be in any order).
            fixture_id: Fixture identifier.
            expected_fixtures: List of expected fixture data.

        Returns:
            Tuple of (home_team, away_team).
        """
        # Find the fixture
        for fixture in expected_fixtures:
            if fixture.get("match_id") == fixture_id:
                home = fixture.get("home_team", "")
                away = fixture.get("away_team", "")
                # Return in correct order
                if home in teams and away in teams:
                    return home, away

        # Fallback: return in original order
        return teams[0], teams[1] if len(teams) > 1 else ""

    def extract(self) -> OCRHints:
        """Extract all OCR hints from cache.

        Main entry point that loads OCR results and extracts all hints.

        Returns:
            OCRHints containing FT graphics and first scoreboards.
        """
        ocr_data = self.load_ocr_results()

        if ocr_data is None:
            return OCRHints()

        return OCRHints(
            ft_graphics=self.extract_ft_graphics(ocr_data),
            first_scoreboards=self.extract_first_scoreboards(ocr_data),
        )

    def format_hints_section(self, hints: OCRHints) -> str:
        """Format hints as markdown section for prompt.

        Args:
            hints: Extracted OCR hints.

        Returns:
            Markdown-formatted hints section.
        """
        if not hints.has_hints:
            return ""

        lines = [
            "## Image Analysis Hints (Advisory)",
            "",
            "The following timestamps were detected via automated image analysis.",
            "These are hints to help anchor your analysis - they may contain errors.",
            "",
        ]

        if hints.ft_graphics:
            lines.append("### Full-Time Graphics Detected")
            lines.append("")
            for ft in hints.ft_graphics:
                lines.append(
                    f"- {ft.timestamp_formatted} - {ft.home_team} vs {ft.away_team}"
                )
            lines.append("")

        if hints.first_scoreboards:
            lines.append("### First Scoreboard Appearances")
            lines.append("")
            lines.append(
                "*(Suggests when highlights/match action may have begun for each match.)*"
            )
            lines.append(
                "*Note: Early detections may be from intro montage, not actual match footage)*"
            )
            lines.append("")
            for sb in hints.first_scoreboards:
                lines.append(
                    f"- {sb.timestamp_formatted} - {sb.home_team} vs {sb.away_team}"
                )
            lines.append("")

        return "\n".join(lines)
