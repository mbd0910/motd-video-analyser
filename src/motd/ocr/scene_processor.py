"""
Scene processor for OCR-based team detection.

Extracts team detection logic from the monolithic process_scene() function
into a well-structured class following Single Responsibility Principle.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from motd.pipeline.models import Scene, ProcessedScene, TeamMatch, OCRResult
from motd.ocr.reader import OCRReader
from motd.ocr.team_matcher import TeamMatcher
from motd.ocr.fixture_matcher import FixtureMatcher


@dataclass
class EpisodeContext:
    """Context for processing scenes from a single episode."""
    episode_id: str
    expected_teams: list[str]
    expected_fixtures: list[dict[str, Any]]


class SceneProcessor:
    """
    Processes individual scenes: OCR -> team matching -> validation.

    Replaces the monolithic process_scene() function with a class that follows
    Single Responsibility Principle - each method does ONE thing.
    """

    def __init__(
        self,
        ocr_reader: OCRReader,
        team_matcher: TeamMatcher,
        fixture_matcher: FixtureMatcher,
        context: EpisodeContext
    ):
        """
        Initialize scene processor with dependencies.

        Args:
            ocr_reader: OCR extraction service
            team_matcher: Fuzzy team matching service
            fixture_matcher: Fixture validation service
            context: Episode-level context (expected teams, fixtures)
        """
        self.ocr_reader = ocr_reader
        self.team_matcher = team_matcher
        self.fixture_matcher = fixture_matcher
        self.context = context
        self.logger = logging.getLogger(__name__)

    def process(self, scene: Scene) -> ProcessedScene | None:
        """
        Process scene: PRIORITIZE FT graphics for segment classification.

        Two-pass strategy ensures FT graphics (match boundary markers) are
        detected even when scoreboards appear earlier in the frame list.

        Pass 1: Search all frames for FT graphics (critical for segment boundaries)
        Pass 2: If no FT found, accept any valid detection (scoreboard/formation)

        Why: Segment classifier (Task 011c) needs FT graphics to detect
        match → post-match transitions. Scoreboards appear throughout match
        footage but don't mark definitive boundaries.

        Args:
            scene: Scene with one or more frames to analyze

        Returns:
            ProcessedScene if teams detected and validated in any frame, None otherwise
        """
        if not scene.frames:
            self.logger.debug(f"Scene {scene.scene_number}: No frames available")
            return None

        # PASS 1: Prioritize FT graphics for segment classification
        for frame_path_str in scene.frames:
            frame = Path(frame_path_str)

            if not frame.exists():
                self.logger.debug(f"Scene {scene.scene_number}: Frame not found: {frame}")
                continue

            result = self._process_single_frame(scene, frame)
            if result and result.ocr_source == 'ft_score':
                self.logger.info(
                    f"Scene {scene.scene_number}: FT graphic detected at {frame.name} "
                    f"({result.team1} vs {result.team2})"
                )
                return result

        # PASS 2: No FT graphic found, accept any valid detection
        for frame_path_str in scene.frames:
            frame = Path(frame_path_str)

            if not frame.exists():
                continue

            result = self._process_single_frame(scene, frame)
            if result:
                self.logger.debug(
                    f"Scene {scene.scene_number}: Fallback detection "
                    f"({result.ocr_source}, {result.team1} vs {result.team2})"
                )
                return result

        # No valid detections in any frame
        return None

    def _process_single_frame(self, scene: Scene, frame: Path) -> ProcessedScene | None:
        """
        Process a single frame: OCR → team matching → validation → fixture ordering.

        Pipeline:
        1. Run OCR with fallback strategy
        2. Match teams from OCR text
        3. Infer opponent if only 1 team detected (FT graphics)
        4. Validate FT graphics
        5. Validate fixture pair
        6. Build result

        Args:
            scene: Parent scene (for metadata)
            frame: Specific frame to process

        Returns:
            ProcessedScene if teams detected and validated, None otherwise
        """
        try:
            # Step 1: Run OCR
            ocr_result = self._run_ocr(frame)
            if not ocr_result:
                return None

            # Step 2: Match teams
            teams = self._match_teams(ocr_result)
            if not teams:
                return None

            # Step 3: Handle single-team FT graphics (opponent inference)
            if len(teams) == 1 and ocr_result.primary_source == 'ft_score':
                inferred = self._infer_opponent(teams[0], ocr_result)
                if inferred:
                    teams.append(inferred)
                else:
                    self.logger.debug(
                        f"Scene {scene.scene_number}: Only 1 team detected, "
                        f"couldn't infer opponent, rejecting"
                    )
                    return None

            # Step 4: Validate FT graphics
            if ocr_result.primary_source == 'ft_score':
                if not self._validate_ft_graphic(ocr_result, teams):
                    self.logger.debug(
                        f"Scene {scene.scene_number}: FT validation failed"
                    )
                    # TODO: Implement scoreboard fallback when FT validation fails
                    # See docs/architecture.md "Pass 2: Accept scoreboards if no FT found"
                    return None

            # Step 5: Validate fixture pair
            validated_teams, fixture = self._validate_fixture_pair(teams)
            if not validated_teams:
                return None

            # Step 6: Build result
            return self._build_result(scene, frame, ocr_result, validated_teams, fixture)

        except Exception as e:
            self.logger.error(f"Error processing frame {frame}: {e}")
            return None

    def _run_ocr(self, frame: Path) -> OCRResult | None:
        """
        Run OCR with fallback strategy (FT score → scoreboard).

        Args:
            frame: Path to frame image

        Returns:
            OCRResult with extracted text, or None if extraction failed
        """
        ocr_dict = self.ocr_reader.extract_with_fallback(frame)

        if not ocr_dict['results']:
            self.logger.debug(f"OCR extraction failed for {frame}")
            return None

        # Convert dict to Pydantic model
        return OCRResult(
            primary_source=ocr_dict['primary_source'],
            results=ocr_dict['results'],
            confidence=ocr_dict.get('confidence', 0.0)
        )

    def _match_teams(self, ocr_result: OCRResult) -> list[TeamMatch]:
        """
        Match teams from OCR text using fuzzy matching.

        Args:
            ocr_result: OCR extraction result

        Returns:
            List of matched teams (0-5 teams for alternative fixture search)
        """
        # Combine text from OCR results
        combined_text = ' '.join([r['text'] for r in ocr_result.results])

        if not combined_text or not combined_text.strip():
            return []

        # OCR NOISE FILTERING: Remove common OCR errors
        noise_terms = ['eeagie', 'eeague', 'bb sport', 'bbc sport']
        combined_text_lower = combined_text.lower()
        for term in noise_terms:
            combined_text_lower = combined_text_lower.replace(term, '')
        combined_text = combined_text_lower

        # Match teams (get top 5 for alternative fixture search)
        matches = self.team_matcher.match_multiple(
            combined_text,
            candidate_teams=self.context.expected_teams,
            max_teams=5
        )

        if not matches:
            return []

        # Convert to Pydantic models
        return [
            TeamMatch(
                team=match['team'],
                confidence=match['confidence'],
                matched_text=match['matched_text'],
                source='ocr'
            )
            for match in matches
        ]

    def _infer_opponent(self, detected_team: TeamMatch, ocr_result: OCRResult) -> TeamMatch | None:
        """
        Infer opponent from fixtures when only 1 team detected.

        Handles OCR failures on non-bold text (e.g., "Aston Villa" in FT graphics).

        Args:
            detected_team: The single team that was detected
            ocr_result: OCR result (must be from ft_score region)

        Returns:
            Inferred opponent as TeamMatch, or None if can't infer
        """
        # Validate this looks like FT graphic
        if not self.ocr_reader.validate_ft_graphic(ocr_result.results, [detected_team.team]):
            return None

        # Find opponent from fixtures
        # BUGFIX: Use 'expected_matches' instead of 'fixtures' (correct key from manifest)
        episode_data = self.fixture_matcher.episodes_by_id.get(self.context.episode_id)
        if not episode_data:
            self.logger.debug(f"No episode data found for {self.context.episode_id}")
            return None

        # Iterate through expected matches to find opponent
        for match_id in episode_data.get('expected_matches', []):  # FIXED: was 'fixtures'
            fixture = self.fixture_matcher.get_fixture_by_id(match_id)
            if not fixture:
                continue

            # Check if detected team is home or away
            if fixture['home_team'] == detected_team.team:
                opponent = fixture['away_team']
                self.logger.debug(
                    f"Inferred opponent from fixture: {detected_team.team} (home) "
                    f"vs {opponent} (away)"
                )
                return TeamMatch(
                    team=opponent,
                    confidence=0.75,  # Lower confidence (inferred, not OCR'd)
                    matched_text='',
                    source='inferred_from_fixture'
                )
            elif fixture['away_team'] == detected_team.team:
                opponent = fixture['home_team']
                self.logger.debug(
                    f"Inferred opponent from fixture: {opponent} (home) "
                    f"vs {detected_team.team} (away)"
                )
                return TeamMatch(
                    team=opponent,
                    confidence=0.75,
                    matched_text='',
                    source='inferred_from_fixture'
                )

        self.logger.debug(
            f"Couldn't find opponent for {detected_team.team} in episode fixtures"
        )
        return None

    def _validate_ft_graphic(self, ocr_result: OCRResult, teams: list[TeamMatch]) -> bool:
        """
        Validate that OCR result is from genuine FT graphic.

        Checks for:
        - At least 1 team detected (allows opponent inference)
        - Score pattern present (e.g., "2-1", "0 0")
        - FT indicator text present

        Args:
            ocr_result: OCR extraction result
            teams: Detected teams

        Returns:
            True if valid FT graphic, False otherwise
        """
        team_names = [t.team for t in teams]
        return self.ocr_reader.validate_ft_graphic(ocr_result.results, team_names)

    def _validate_fixture_pair(self, teams: list[TeamMatch]) -> tuple[list[TeamMatch], dict[str, Any] | None]:
        """
        Validate that detected teams form a valid fixture pair.

        Prevents false matches like "Chelsea vs Man Utd" when actual fixture
        is "Forest vs Man Utd" (OCR read "che" from "Manchester").

        Args:
            teams: List of detected teams (should be 2)

        Returns:
            Tuple of (validated_teams, matched_fixture) if valid, (None, None) otherwise
        """
        if len(teams) < 2:
            self.logger.debug(f"Not enough teams detected: {len(teams)}")
            return None, None

        team1, team2 = teams[0].team, teams[1].team
        fixture = self.fixture_matcher.identify_fixture(team1, team2, self.context.episode_id)

        if fixture:
            # Valid pair! Order teams by fixture (home, away)
            ordered_teams = self._order_teams_by_fixture(teams, fixture)
            return ordered_teams, fixture

        # Invalid pair! Search for alternative valid pair in top candidates
        self.logger.debug(
            f"Top 2 teams ({team1}, {team2}) don't form valid fixture, "
            f"searching alternatives..."
        )

        # Try all combinations of top N teams to find a valid fixture
        # This handles false positives from fuzzy matching (e.g., "ham" matching West Ham)
        max_candidates = min(len(teams), 5)  # Check up to top 5 teams
        best_fixture = None
        best_teams = None
        best_confidence = 0.0

        for i in range(max_candidates):
            for j in range(i + 1, max_candidates):
                team_i, team_j = teams[i], teams[j]
                fixture = self.fixture_matcher.identify_fixture(
                    team_i.team, team_j.team, self.context.episode_id
                )

                if fixture:
                    # Found a valid fixture! Calculate combined confidence
                    combined_confidence = team_i.confidence + team_j.confidence

                    # Keep track of the highest confidence valid fixture
                    if combined_confidence > best_confidence:
                        best_fixture = fixture
                        best_teams = [team_i, team_j]
                        best_confidence = combined_confidence

                        self.logger.debug(
                            f"Alternative fixture found: teams #{i+1} + #{j+1} "
                            f"({team_i.team} vs {team_j.team}, "
                            f"combined confidence: {combined_confidence:.2f})"
                        )

        if best_fixture:
            # Found at least one valid fixture in alternatives
            ordered_teams = self._order_teams_by_fixture(best_teams, best_fixture)
            self.logger.info(
                f"Using alternative fixture: {best_fixture['match_id']} "
                f"({ordered_teams[0].team} vs {ordered_teams[1].team})"
            )
            return ordered_teams, best_fixture

        # No valid fixture found in any combination
        self.logger.debug(
            f"No valid fixture found in top {max_candidates} teams"
        )
        return None, None

    def _order_teams_by_fixture(self, teams: list[TeamMatch], fixture: dict[str, Any]) -> list[TeamMatch]:
        """
        Order teams by fixture (home first, then away).

        Args:
            teams: Detected teams (may be in wrong order)
            fixture: Matched fixture with home_team and away_team

        Returns:
            Teams ordered as [home, away]
        """
        team1, team2 = teams[0], teams[1]

        # Check if teams are in wrong order (away team listed first)
        if team1.team == fixture['away_team'] and team2.team == fixture['home_team']:
            self.logger.debug(
                f"Swapping team order to match fixture: "
                f"{team1.team} vs {team2.team} � {team2.team} vs {team1.team}"
            )
            return [team2, team1]

        return [team1, team2]

    def _build_result(
        self,
        scene: Scene,
        frame: Path,
        ocr_result: OCRResult,
        teams: list[TeamMatch],
        fixture: dict[str, Any] | None
    ) -> ProcessedScene:
        """
        Build final ProcessedScene result.

        Args:
            scene: Original scene
            frame: Frame path that was analyzed
            ocr_result: OCR extraction result
            teams: Validated teams (ordered by fixture)
            fixture: Matched fixture (if any)

        Returns:
            ProcessedScene with all metadata
        """
        # Calculate overall confidence (average of team confidences)
        match_confidence = sum(t.confidence for t in teams) / len(teams)

        return ProcessedScene(
            scene_number=scene.scene_number,
            start_time=scene.start_time,
            start_seconds=scene.start_seconds,
            frame_path=str(frame),
            ocr_source=ocr_result.primary_source,
            team1=teams[0].team,
            team2=teams[1].team,
            match_confidence=match_confidence,
            fixture_id=fixture['match_id'] if fixture else None,
            home_team=fixture['home_team'] if fixture else None,
            away_team=fixture['away_team'] if fixture else None
        )
