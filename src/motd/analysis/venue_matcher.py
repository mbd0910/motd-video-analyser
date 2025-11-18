"""
Venue matching for transcript-based match boundary detection.

VenueMatcher performs fuzzy matching on venue mentions in transcripts to identify
which stadium is being referenced. Used in Strategy 2 of boundary detection.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz


@dataclass
class VenueMatch:
    """Result of a venue matching operation."""

    venue: str  # Official stadium name
    team: str  # Team that plays there
    confidence: float  # 0.0-1.0
    matched_text: str  # Text that triggered the match
    source: str  # "stadium" | "alias" | "additional_reference"


class VenueMatcher:
    """
    Fuzzy matcher for venue mentions in transcripts.

    Matches stadium names, aliases, and additional references (stands, former venues)
    with different confidence levels based on match source.

    Confidence scores:
    - Stadium name match: 1.0 (exact or high fuzzy match)
    - Alias match: 0.9
    - Additional reference match: 0.7 (lower - less definitive)

    Example usage:
        matcher = VenueMatcher('data/venues/premier_league_2025_26.json')
        result = matcher.match_venue("at Anfield")
        # VenueMatch(venue="Anfield", team="Liverpool", confidence=1.0, ...)
    """

    def __init__(self, venues_json_path: str):
        """
        Load venue data and build search indices.

        Args:
            venues_json_path: Path to venues JSON file
        """
        venues_path = Path(venues_json_path)
        with open(venues_path) as f:
            data = json.load(f)

        self.venues = data["venues"]
        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup dictionaries for fast matching."""
        self.stadium_index = {}  # {stadium_clean: venue_data}
        self.alias_index = {}  # {alias_clean: venue_data}
        self.additional_ref_index = {}  # {ref_clean: venue_data}

        for venue in self.venues:
            team = venue["team"]
            stadium = venue["stadium"]

            # Stadium name index - use cleaned keys
            cleaned_stadium = self._clean_text(stadium)
            self.stadium_index[cleaned_stadium] = venue

            # Alias index - use cleaned keys
            for alias in venue.get("aliases", []):
                cleaned_alias = self._clean_text(alias)
                self.alias_index[cleaned_alias] = venue

            # Additional references index - use cleaned keys
            for ref in venue.get("additional_references", []):
                cleaned_ref = self._clean_text(ref)
                self.additional_ref_index[cleaned_ref] = venue

    def match_venue(
        self, text: str, team_context: Optional[str] = None, threshold: float = 0.65
    ) -> Optional[VenueMatch]:
        """
        Fuzzy match venue mention in text.

        Searches in priority order:
        1. Stadium names (confidence 1.0)
        2. Aliases (confidence 0.9)
        3. Additional references (confidence 0.7)

        Args:
            text: Transcript segment text
            team_context: Optional expected team (for disambiguation)
            threshold: Minimum confidence to return a match (default: 0.65)

        Returns:
            VenueMatch if match found above threshold, None otherwise

        Examples:
            >>> matcher.match_venue("at Anfield")
            VenueMatch(venue="Anfield", team="Liverpool", confidence=1.0, ...)

            >>> matcher.match_venue("The Emirates")
            VenueMatch(venue="Emirates Stadium", team="Arsenal", confidence=0.9, ...)

            >>> matcher.match_venue("The Kop")
            VenueMatch(venue="Anfield", team="Liverpool", confidence=0.7, ...)
        """
        # Clean text for matching
        cleaned_text = self._clean_text(text)

        # Try stadium name match ONLY (no aliases to prevent false positives)
        match = self._try_index_match(
            cleaned_text, self.stadium_index, confidence=1.0, source="stadium"
        )
        if match and match.confidence >= threshold:
            return match

        # REMOVED: Alias matching (caused false positives like "that lane" matching "The Lane")
        # REMOVED: Additional reference matching (too ambiguous for reliable detection)

        return None

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for matching.

        Removes common prepositions and articles to improve matching.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove common prepositions/articles at start
        patterns = [
            r"^at\s+",
            r"^the\s+",
            r"^in\s+",
            r"^to\s+",
        ]

        cleaned = text.lower().strip()
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned

    def _try_index_match(
        self, cleaned_text: str, index: dict, confidence: float, source: str
    ) -> Optional[VenueMatch]:
        """
        Try to match against a specific index.

        Uses rapidfuzz for fuzzy matching to handle OCR/transcription errors.

        Args:
            cleaned_text: Normalized text to match
            index: Index dictionary to search
            confidence: Base confidence for this source
            source: Source identifier for match metadata

        Returns:
            VenueMatch if found, None otherwise
        """
        best_match = None
        best_score = 0.0

        for key, venue in index.items():
            # Try fuzzy match using partial_ratio to find venue names within longer sentences
            score = fuzz.partial_ratio(cleaned_text, key) / 100.0

            if score > best_score:
                best_score = score
                best_match = venue

        # Return match if score is high enough
        # Apply base confidence weighted by fuzzy match score
        # Lower threshold for shorter texts (2-3 words) where fuzzy match is harder
        min_score = 0.70 if len(cleaned_text.split()) <= 3 else 0.85

        if best_match and best_score >= min_score:
            final_confidence = confidence * best_score

            return VenueMatch(
                venue=best_match["stadium"],
                team=best_match["team"],
                confidence=final_confidence,
                matched_text=cleaned_text,
                source=source,
            )

        return None

    def get_venue_for_team(self, team_name: str) -> Optional[str]:
        """
        Get the stadium name for a given team.

        Args:
            team_name: Full team name

        Returns:
            Stadium name or None if team not found
        """
        for venue in self.venues:
            if venue["team"] == team_name:
                return venue["stadium"]

        return None
