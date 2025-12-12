"""Prompt builder for LLM-based transcript analysis.

Assembles the complete prompt including fixtures, instructions,
output schema, OCR hints, and formatted transcript.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from motd.llm.ocr_hints import OCRHintsExtractor, OCRHints
from motd.llm.transcript_formatter import TranscriptFormatter, FormattedTranscript

logger = logging.getLogger(__name__)


@dataclass
class Fixture:
    """A Premier League fixture."""

    match_id: str
    date: str
    home_team: str
    away_team: str
    venue: str
    kickoff: str = ""
    final_score: dict[str, int] | None = None


@dataclass
class BuiltPrompt:
    """Result of prompt building."""

    content: str
    transcript_stats: FormattedTranscript
    fixture_count: int
    has_ocr_hints: bool
    estimated_tokens: int


class PromptBuilder:
    """Builds complete LLM prompts for episode analysis.

    Assembles fixtures, instructions, output schema, OCR hints,
    and formatted transcript into a single prompt ready for
    copy-paste into Claude web UI.
    """

    # Default paths relative to project root
    DEFAULT_FIXTURES_PATH = Path("data/fixtures/premier_league_2025_26.json")
    DEFAULT_MANIFEST_PATH = Path("data/episodes/episode_manifest.json")

    def __init__(
        self,
        cache_path: Path | str,
        include_hints: bool = True,
        fixtures_path: Path | None = None,
        manifest_path: Path | None = None,
    ) -> None:
        """Initialise prompt builder.

        Args:
            cache_path: Path to episode cache folder.
            include_hints: Whether to include OCR advisory hints.
            fixtures_path: Optional custom path to fixtures JSON file.
            manifest_path: Optional custom path to episode manifest JSON file.
        """
        self.cache_path = Path(cache_path)
        self.include_hints = include_hints
        self.fixtures_path = fixtures_path or self.DEFAULT_FIXTURES_PATH
        self.manifest_path = manifest_path or self.DEFAULT_MANIFEST_PATH

        # Extract episode_id from cache path
        self.episode_id = self.cache_path.name

        # Initialise sub-components
        self.transcript_formatter = TranscriptFormatter(cache_path)
        self.ocr_extractor = OCRHintsExtractor(cache_path) if include_hints else None

    def load_episode_from_manifest(self) -> dict[str, Any] | None:
        """Load episode metadata from manifest.

        Returns:
            Episode data dict or None if not found.
        """
        if not self.manifest_path.exists():
            logger.warning("Episode manifest not found: %s", self.manifest_path)
            return None

        with open(self.manifest_path) as f:
            manifest = json.load(f)

        for episode in manifest.get("episodes", []):
            if episode.get("episode_id") == self.episode_id:
                return episode

        logger.warning("Episode %s not found in manifest", self.episode_id)
        return None

    def load_fixtures_for_episode(
        self, episode: dict[str, Any] | None = None
    ) -> list[Fixture]:
        """Load fixtures for this episode's date.

        Args:
            episode: Optional pre-loaded episode data to avoid duplicate manifest loading.

        Returns:
            List of Fixture objects for the episode date.
        """
        if episode is None:
            episode = self.load_episode_from_manifest()
        if not episode:
            return []

        broadcast_date = episode.get("broadcast_date")
        expected_match_ids = set(episode.get("expected_matches", []))

        if not self.fixtures_path.exists():
            logger.warning("Fixtures file not found: %s", self.fixtures_path)
            return []

        with open(self.fixtures_path) as f:
            fixtures_data = json.load(f)

        fixtures: list[Fixture] = []
        for fix in fixtures_data.get("fixtures", []):
            match_id = fix.get("match_id", "")
            # Include if in expected_matches OR matches the date
            if match_id in expected_match_ids or fix.get("date") == broadcast_date:
                fixtures.append(
                    Fixture(
                        match_id=match_id,
                        date=fix.get("date", ""),
                        home_team=fix.get("home_team", ""),
                        away_team=fix.get("away_team", ""),
                        venue=fix.get("venue", ""),
                        kickoff=fix.get("kickoff", ""),
                        final_score=fix.get("final_score"),
                    )
                )

        logger.info("Loaded %d fixtures for episode", len(fixtures))
        return fixtures

    def _build_header(self, episode: dict[str, Any] | None) -> str:
        """Build prompt header section."""
        broadcast_date = "Unknown"
        if episode:
            broadcast_date = episode.get("broadcast_date", "Unknown")

        return f"""# BBC Match of the Day Analysis Request

**Episode Date:** {broadcast_date}
**Broadcast:** BBC One
**Episode ID:** {self.episode_id}
"""

    def _build_fixtures_table(self, fixtures: list[Fixture]) -> str:
        """Build fixtures table section."""
        if not fixtures:
            return "## Fixtures\n\n*No fixtures data available*\n"

        lines = [
            "## Fixtures This Gameweek",
            "",
            f"These {len(fixtures)} Premier League matches were played and are covered in this episode:",
            "",
            "| Home | Away | Venue | Score |",
            "|------|------|-------|-------|",
        ]

        for fix in fixtures:
            score = "TBC"
            if fix.final_score:
                score = f"{fix.final_score.get('home', '?')}-{fix.final_score.get('away', '?')}"
            lines.append(f"| {fix.home_team} | {fix.away_team} | {fix.venue} | {score} |")

        lines.append("")
        return "\n".join(lines)

    def _build_task_description(self) -> str:
        """Build task description section."""
        return """## Task

Analyse the transcript and identify the episode structure. The running order (which match is shown first, second, etc.) is determined by **editorial choice**, NOT the fixture list above.

### Episode-Level Segments

Identify these episode segments (all have start and end timestamps):

- **intro** - Opening sequence ("Welcome to Match of the Day", pundit introductions)
- **league_table** - League standings review (if present)
- **next_motd_promo** - Promotional segment for next MOTD episode (if present)
- **outro** - Closing credits/sign-off

### Match Segments

For each match, identify these segments in order:

1. **studio_intro** - When pundits/presenter start discussing this match
   - STARTS: When they begin talking about the upcoming match
   - ENDS: At the commentator credit ("Your commentator, [name]" or "[name] was at [venue]")

2. **lineups** - Formation graphics and team walkthrough
   - STARTS: After commentator credit
   - ENDS: When actual match action begins (scoreboard appears in corner)

3. **highlights** - Match footage with live commentary
   - STARTS: When match action begins (scoreboard visible)
   - ENDS: At full-time announcement or transition to interviews

4. **post_match_interviews** - Player/manager pitchside interviews (if any)
   - May have multiple interviewees back-to-back

5. **studio_analysis** - Pundits back in studio discussing the match (if any)
   - May include tactical analysis, replays, pundit debate

### Important Notes

- The **running order is editorial choice** - the first match shown may not be the biggest game
- **studio_intro starts** when they BEGIN discussing the match, not when the commentator is credited
- **Commentator credit marks the END of studio_intro** and START of lineups
- Use the **Image Analysis Hints** below (if provided) to help identify transitions
- Timestamps should be in MM:SS format
- Start and end can independently be null if unclear (e.g., `"start": "12:30", "end": null`)
"""

    def _build_output_schema(self) -> str:
        """Build output schema section."""
        schema = {
            "episode": {
                "date": "YYYY-MM-DD",
                "intro": {"start": "MM:SS", "end": "MM:SS"},
                "league_table": {"start": "MM:SS|null", "end": "MM:SS|null"},
                "next_motd_promo": {"start": "MM:SS|null", "end": "MM:SS|null"},
                "outro": {"start": "MM:SS|null", "end": "MM:SS|null"},
            },
            "matches": [
                {
                    "order": 1,
                    "home_team": "Team Name",
                    "away_team": "Team Name",
                    "venue": "Stadium Name",
                    "score": {"home": 0, "away": 0},
                    "segments": {
                        "studio_intro": {"start": "MM:SS", "end": "MM:SS|null"},
                        "lineups": {"start": "MM:SS|null", "end": "MM:SS|null"},
                        "highlights": {"start": "MM:SS", "end": "MM:SS"},
                        "post_match_interviews": {"start": "MM:SS|null", "end": "MM:SS|null"},
                        "studio_analysis": {"start": "MM:SS|null", "end": "MM:SS|null"},
                    },
                    "notes": "Any observations or edge cases",
                }
            ],
        }

        return f"""## Output Format

Return valid JSON matching this structure:

```json
{json.dumps(schema, indent=2)}
```

**Rules:**
- `order` indicates the running order (1 = first match shown, 2 = second, etc.)
- Each segment has `start` and `end` - both can independently be `null` if unclear
- Use MM:SS format for timestamps (e.g., "12:30" not "00:12:30")
- Include `notes` for any edge cases or observations
"""

    def _build_transcript_section(self, formatted: FormattedTranscript) -> str:
        """Build transcript section."""
        duration_mins = formatted.duration_seconds / 60
        return f"""## Transcript

**Duration:** {duration_mins:.1f} minutes
**Segments:** {formatted.segment_count} (after deduplication)

{formatted.text}
"""

    def build(self) -> BuiltPrompt:
        """Build the complete prompt.

        Returns:
            BuiltPrompt containing the full prompt text and metadata.
        """
        # Load data (pass episode to avoid duplicate manifest loading)
        episode = self.load_episode_from_manifest()
        fixtures = self.load_fixtures_for_episode(episode)
        formatted_transcript = self.transcript_formatter.format()

        # Extract OCR hints if enabled
        ocr_hints: OCRHints | None = None
        hints_section = ""
        if self.ocr_extractor:
            ocr_hints = self.ocr_extractor.extract()
            if ocr_hints.has_hints:
                hints_section = self.ocr_extractor.format_hints_section(ocr_hints)

        # Build prompt sections
        sections = [
            self._build_header(episode),
            self._build_fixtures_table(fixtures),
            self._build_task_description(),
            self._build_output_schema(),
        ]

        # Add hints if available
        if hints_section:
            sections.append(hints_section)

        # Add transcript last (largest section)
        sections.append(self._build_transcript_section(formatted_transcript))

        content = "\n".join(sections)

        # Estimate tokens (rough: ~4 chars per token)
        estimated_tokens = len(content) // 4

        return BuiltPrompt(
            content=content,
            transcript_stats=formatted_transcript,
            fixture_count=len(fixtures),
            has_ocr_hints=ocr_hints.has_hints if ocr_hints else False,
            estimated_tokens=estimated_tokens,
        )
