"""
Validation logic for FT graphics and scoreboards.

This module contains PURE business logic with NO ML dependencies (torch, easyocr, cv2).
Can be imported and tested without loading heavy ML frameworks (~2GB).

Extracted from OCRReader as part of Issue #9 (CI/CD setup) to enable:
- Fast unit tests (~10s vs ~80s)
- Clean separation of concerns (validation logic vs ML inference)
- Dependency injection for testing
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GraphicValidator:
    """
    Validates OCR results for FT graphics and scoreboards.

    Pure business logic - no ML dependencies. Uses regex patterns and
    string matching to determine if OCR results represent genuine
    FT graphics or scoreboards vs noise (possession bars, studio overlays, etc.).

    Can be instantiated with team codes directly (for testing) or via
    the from_teams_file() factory method (for production).
    """

    # Class-level constants for validation
    FT_INDICATORS = ['FT', 'FULL TIME', 'FULL-TIME', 'FULLTIME']

    # Matches "2-1", "0 - 0", "2 0", "3 | 0", etc.
    # BBC FT graphics show "2 | 0" and OCR may read hyphen, pipe, or space
    SCORE_PATTERN = r'\b\d+\s*[-–—|]?\s*\d+\b'

    def __init__(self, team_codes: set[str]):
        """
        Initialise validator with team codes.

        Args:
            team_codes: Set of valid 3-character team codes (uppercase).
                       Example: {'LIV', 'AVL', 'ARS', 'CHE', 'MUN'}
        """
        self.valid_team_codes = team_codes
        logger.debug(f"GraphicValidator initialised with {len(team_codes)} team codes")

    @classmethod
    def from_teams_file(cls, teams_path: Path) -> GraphicValidator:
        """
        Factory method to create validator from teams JSON file.

        Args:
            teams_path: Path to teams JSON file (e.g., premier_league_2025_26.json)

        Returns:
            GraphicValidator with team codes loaded from file

        Raises:
            FileNotFoundError: If teams file not found
            json.JSONDecodeError: If teams file is invalid JSON
        """
        codes = cls._load_team_codes(teams_path)
        return cls(codes)

    @staticmethod
    def _load_team_codes(teams_path: Path) -> set[str]:
        """
        Load valid 3-character team codes from teams JSON file.

        Args:
            teams_path: Path to teams JSON file

        Returns:
            Set of valid team codes (uppercase) for exact matching

        Raises:
            FileNotFoundError: If teams file not found
            json.JSONDecodeError: If teams file is invalid JSON
        """
        if not teams_path.exists():
            raise FileNotFoundError(
                f"Teams file not found: {teams_path}. "
                f"Ensure config['teams']['path'] points to valid file."
            )

        with open(teams_path, encoding='utf-8') as f:
            teams_data = json.load(f)

        # Extract all codes from all teams
        codes = set()
        for team in teams_data.get('teams', []):
            for code in team.get('codes', []):
                codes.add(code.upper())

        logger.debug(f"Loaded {len(codes)} team codes from {teams_path}")
        return codes

    def validate_ft_graphic(self, ocr_results: list[dict[str, Any]], detected_teams: list[str]) -> bool:
        """
        Validate that OCR results are from a genuine FT score graphic.

        Uses two-tier validation to prioritise strong signals (teams + FT) over weak signals (score):

        **Tier 1 (STRONG):** ≥1 team + FT indicator
        - Score pattern is OPTIONAL (may have low OCR confidence)
        - Most reliable signal: team names + "FT" text confirms end-of-match graphic
        - Example: "Liverpool 2 FT" (score "0" missing due to low confidence)

        **Tier 2 (FALLBACK):** Score pattern + FT indicator
        - No teams detected (OCR failed on team names)
        - Numeric score + FT still indicates genuine FT graphic
        - Example: "3 1 FT" (team names completely missed)

        This filters out:
        - Possession bars (no FT text)
        - Player statistics (no FT text)
        - Formation graphics (team names but no FT)
        - Studio overlays (team mentions but no FT)

        Args:
            ocr_results: List of raw OCR results (dicts with 'text' key)
            detected_teams: List of matched team names

        Returns:
            True if this is a genuine FT graphic, False otherwise
        """
        # Extract all OCR text
        all_text = ' '.join([r.get('text', '').upper() for r in ocr_results])

        # Check for FT indicator
        has_ft = any(indicator in all_text for indicator in self.FT_INDICATORS)

        # Check for score pattern
        has_score = bool(re.search(self.SCORE_PATTERN, all_text))

        # Tier 1: Team name(s) + FT indicator (STRONG signal)
        if len(detected_teams) >= 1 and has_ft:
            logger.debug(
                f"FT validation passed (Tier 1): {detected_teams} + FT indicator"
            )
            return True

        # Tier 2: Score pattern + FT indicator (FALLBACK for missed teams)
        if has_score and has_ft:
            logger.debug(
                "FT validation passed (Tier 2): score pattern + FT indicator (no teams detected)"
            )
            return True

        # Failed both tiers
        logger.debug(
            f"FT validation failed: teams={len(detected_teams)}, "
            f"score={has_score}, ft_text={has_ft}"
        )
        return False

    def validate_scoreboard(self, ocr_results: list[dict[str, Any]]) -> bool:
        """
        Validate that OCR results are from a genuine scoreboard graphic.

        BBC scoreboards follow format: "BBC [CODE] [SCORE]|[SCORE] [CODE]"
        Example: "BBC LIV 0|0 FOR"

        Requirement (relaxed - Issue #17):
        - At least 2 distinct 3-character team codes (from teams JSON)

        Note: Score pattern requirement removed because OCR from cropped
        scoreboard region (0,0 to 370x70) doesn't always capture the score.
        Two distinct team codes is sufficient to distinguish real scoreboards
        from noise (intro montage, studio overlays, etc.).

        This filters out:
        - Intro montage graphics ("The CL UB BALL")
        - Studio overlays with team mentions but no codes
        - Partial/corrupt OCR reads

        Args:
            ocr_results: List of raw OCR results (dicts with 'text' key)

        Returns:
            True if this is a genuine scoreboard, False otherwise
        """
        if not ocr_results:
            return False

        # Extract all OCR text (uppercase for case-insensitive matching)
        all_text = ' '.join([r.get('text', '').upper() for r in ocr_results])

        # Check for at least 2 distinct 3-character team codes
        # Split text into words and find exact matches against valid codes
        words = all_text.split()
        found_codes = set(w for w in words if w in self.valid_team_codes)
        has_two_codes = len(found_codes) >= 2

        if has_two_codes:
            logger.debug(
                f"Scoreboard validation passed: codes={found_codes}"
            )
            return True

        logger.debug(
            f"Scoreboard validation failed: codes={found_codes} (need 2)"
        )
        return False

    def looks_like_ft_content(self, ocr_results: list[dict[str, Any]]) -> bool:
        """
        Quick check if OCR results look like genuine FT graphic content.

        Used to decide whether to accept FT region results or fall back to scoreboard.
        Less strict than validate_ft_graphic() - just checking for relevant content.

        Returns True if results contain:
        - FT indicators ("FT", "FULL TIME", etc.), OR
        - Score pattern (e.g., "2-1", "0 | 0"), OR
        - Valid team codes from the teams file

        Args:
            ocr_results: List of raw OCR results (dicts with 'text' key)

        Returns:
            True if results look like FT content, False otherwise
        """
        if not ocr_results:
            return False

        # Combine all text
        all_text = ' '.join([r.get('text', '').upper() for r in ocr_results])

        # Check for FT indicators
        if any(indicator in all_text for indicator in self.FT_INDICATORS):
            return True

        # Check for score pattern
        if re.search(self.SCORE_PATTERN, all_text):
            return True

        # Check for team codes
        words = all_text.split()
        return any(w in self.valid_team_codes for w in words)
