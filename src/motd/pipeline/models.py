"""
Pydantic models for type-safe data structures in the MOTD analysis pipeline.

These models provide runtime validation, clear contracts between layers,
and make the codebase more maintainable and testable.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Any


class Scene(BaseModel):
    """
    Scene detected by PySceneDetect.

    Represents a continuous segment of video with consistent visual content.
    """
    scene_number: int = Field(..., description="Sequential scene number (1-indexed)")
    start_time: str = Field(..., description="Start time in HH:MM:SS format")
    start_seconds: float = Field(..., ge=0, description="Start time in seconds")
    end_seconds: float = Field(..., ge=0, description="End time in seconds")
    duration: float = Field(..., ge=0, description="Scene duration in seconds")
    frames: list[str] = Field(default_factory=list, description="Paths to extracted frames")
    key_frame_path: str | None = Field(None, description="Path to key/representative frame")

    @field_validator('end_seconds')
    @classmethod
    def validate_end_after_start(cls, v: float, info) -> float:
        """Ensure end time is after start time."""
        if 'start_seconds' in info.data and v <= info.data['start_seconds']:
            raise ValueError('end_seconds must be greater than start_seconds')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scene_number": 1,
                    "start_time": "00:00:15",
                    "start_seconds": 15.0,
                    "end_seconds": 18.5,
                    "duration": 3.5,
                    "frames": ["frame_001.jpg", "frame_002.jpg"],
                    "key_frame_path": "frame_001.jpg"
                }
            ]
        }
    }


class TeamMatch(BaseModel):
    """
    Result of fuzzy matching a team name from OCR text.

    Represents a single team detected via OCR + fuzzy string matching.
    """
    team: str = Field(..., description="Matched team name (canonical form)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence (0.0-1.0)")
    matched_text: str = Field(..., description="Original OCR text that was matched")
    source: str = Field(..., description="Detection source: 'ocr' or 'inferred_from_fixture'")

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Ensure source is one of allowed values."""
        allowed = {'ocr', 'inferred_from_fixture'}
        if v not in allowed:
            raise ValueError(f'source must be one of {allowed}, got {v}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "team": "Liverpool",
                    "confidence": 0.95,
                    "matched_text": "Liverpoo",
                    "source": "ocr"
                },
                {
                    "team": "Aston Villa",
                    "confidence": 0.75,
                    "matched_text": "",
                    "source": "inferred_from_fixture"
                }
            ]
        }
    }


class OCRResult(BaseModel):
    """
    Result of OCR extraction from a frame.

    Contains raw OCR results and metadata about which region was used.
    """
    primary_source: str = Field(
        ...,
        description="Primary OCR region used: 'ft_score', 'scoreboard', or 'formation'"
    )
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Raw OCR results from EasyOCR (list of dicts with text/confidence/bbox)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average confidence across all detected text"
    )

    @field_validator('primary_source')
    @classmethod
    def validate_primary_source(cls, v: str) -> str:
        """Ensure primary_source is one of allowed OCR regions."""
        allowed = {'ft_score', 'scoreboard', 'formation'}
        if v not in allowed:
            raise ValueError(f'primary_source must be one of {allowed}, got {v}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "primary_source": "ft_score",
                    "results": [
                        {"text": "Liverpool", "confidence": 0.95},
                        {"text": "2", "confidence": 0.98},
                        {"text": "Aston Villa", "confidence": 0.92},
                        {"text": "0", "confidence": 0.99},
                        {"text": "FT", "confidence": 0.97}
                    ],
                    "confidence": 0.96
                }
            ]
        }
    }


class ProcessedScene(BaseModel):
    """
    Scene after OCR + team matching + validation.

    Represents a successfully processed scene with detected teams and metadata.
    """
    scene_number: int = Field(..., description="Scene number from original scene")
    start_time: str = Field(..., description="Start time in HH:MM:SS format")
    start_seconds: float = Field(..., ge=0, description="Start time in seconds")
    frame_path: str = Field(..., description="Path to frame that was analyzed")
    ocr_source: str = Field(..., description="OCR region used: ft_score or scoreboard")
    team1: str = Field(..., description="First detected team (not necessarily home)")
    team2: str = Field(..., description="Second detected team (not necessarily away)")
    match_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in team detection"
    )
    fixture_id: str | None = Field(None, description="Fixture ID if teams matched a fixture")
    home_team: str | None = Field(None, description="Home team (after fixture ordering)")
    away_team: str | None = Field(None, description="Away team (after fixture ordering)")

    @field_validator('ocr_source')
    @classmethod
    def validate_ocr_source(cls, v: str) -> str:
        """Ensure ocr_source is one of allowed values."""
        allowed = {'ft_score', 'scoreboard', 'formation'}
        if v not in allowed:
            raise ValueError(f'ocr_source must be one of {allowed}, got {v}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "scene_number": 42,
                    "start_time": "00:10:07",
                    "start_seconds": 607.3,
                    "frame_path": "data/cache/episode/frames/frame_0329.jpg",
                    "ocr_source": "ft_score",
                    "team1": "Liverpool",
                    "team2": "Aston Villa",
                    "match_confidence": 0.88,
                    "fixture_id": "2025-11-01-liverpool-astonvilla",
                    "home_team": "Liverpool",
                    "away_team": "Aston Villa"
                }
            ]
        }
    }


class BoundaryValidation(BaseModel):
    """
    Cross-validation result for match boundary detection.

    Compares venue (primary) vs clustering (validator) strategies to ensure
    detection accuracy and flag discrepancies for manual review.
    """
    status: str = Field(..., description="Validation status: 'validated', 'minor_discrepancy', 'major_discrepancy'")
    venue_timestamp: float | None = Field(None, ge=0, description="Venue strategy timestamp (primary)")
    clustering_timestamp: float | None = Field(None, ge=0, description="Clustering strategy timestamp (validator)")
    difference_seconds: float | None = Field(None, description="Absolute difference between strategies (seconds)")
    agreement: bool = Field(..., description="True if strategies agree within ±10s")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence based on agreement (1.0=validated, 0.8=minor, 0.5=major)")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is one of allowed values."""
        allowed = {'validated', 'minor_discrepancy', 'major_discrepancy', 'clustering_failed'}
        if v not in allowed:
            raise ValueError(f'status must be one of {allowed}, got {v}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "validated",
                    "venue_timestamp": 2509.06,
                    "clustering_timestamp": 2509.06,
                    "difference_seconds": 0.0,
                    "agreement": True,
                    "confidence": 1.0
                },
                {
                    "status": "minor_discrepancy",
                    "venue_timestamp": 1587.21,
                    "clustering_timestamp": 1616.16,
                    "difference_seconds": 28.95,
                    "agreement": False,
                    "confidence": 0.8
                }
            ]
        }
    }


class MatchBoundary(BaseModel):
    """
    Detected boundaries for a single match.

    Contains timestamps for match start, highlights start/end, and match end.
    Used by multi-strategy running order detection and boundary detection.
    """
    teams: tuple[str, str] = Field(..., description="Team pair (normalized/sorted)")
    position: int = Field(..., ge=1, le=7, description="Running order position (1-7)")

    # Timestamps (seconds)
    match_start: float | None = Field(None, ge=0, description="Match segment start (studio intro)")
    highlights_start: float | None = Field(None, ge=0, description="First scoreboard appearance")
    highlights_end: float | None = Field(None, ge=0, description="FT graphic timestamp")
    match_end: float | None = Field(None, ge=0, description="Match segment end (before next match)")

    # Detection metadata
    first_mention_time: float | None = Field(None, ge=0, description="First team mention (OCR/transcript)")
    first_scoreboard_time: float | None = Field(None, ge=0, description="First scoreboard detection")
    ft_graphic_time: float | None = Field(None, ge=0, description="FT graphic detection")
    last_mention_time: float | None = Field(None, ge=0, description="Last team mention")

    # Confidence
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall boundary confidence")
    detection_sources: list[str] = Field(
        default_factory=list,
        description="Detection sources used: 'scoreboard', 'ft_graphic', 'mentions'"
    )

    # Boundary detection strategy results (for analysis/comparison)
    team_mention_result: dict[str, Any] | None = Field(
        None,
        description="Team mention strategy result with timestamp and details"
    )
    venue_result: dict[str, Any] | None = Field(
        None,
        description="Venue strategy result with timestamp and venue details"
    )
    clustering_result: dict[str, Any] | None = Field(
        None,
        description="Clustering strategy result with timestamp, density, and cluster metadata"
    )

    # Cross-validation (venue as primary, clustering as validator)
    validation: BoundaryValidation | None = Field(
        None,
        description="Cross-validation result comparing venue vs clustering strategies"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "teams": ("Liverpool", "Aston Villa"),
                    "position": 1,
                    "match_start": 50.0,
                    "highlights_start": 112.0,
                    "highlights_end": 607.3,
                    "match_end": 911.0,
                    "first_mention_time": 48.5,
                    "first_scoreboard_time": 112.0,
                    "ft_graphic_time": 607.3,
                    "last_mention_time": 910.2,
                    "confidence": 0.95,
                    "detection_sources": ["scoreboard", "ft_graphic", "mentions"]
                }
            ]
        }
    }


class RunningOrderResult(BaseModel):
    """
    Result of multi-strategy running order detection.

    Contains ordered list of matches with boundaries and cross-validation metadata.
    """
    matches: list[MatchBoundary] = Field(..., description="Ordered list of matches (running order)")
    strategy_results: dict[str, list[tuple[str, str]]] = Field(
        ...,
        description="Results from each strategy: 'scoreboard', 'ft_graphic', 'mentions'"
    )
    consensus_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cross-validation confidence (1.0 = all strategies agree)"
    )
    disagreements: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Positions where strategies disagreed"
    )

    @field_validator('matches')
    @classmethod
    def validate_positions_sequential(cls, v: list[MatchBoundary]) -> list[MatchBoundary]:
        """Ensure positions are 1,2,3,...,7 with no gaps."""
        positions = [m.position for m in v]
        expected = list(range(1, len(v) + 1))
        if positions != expected:
            raise ValueError(f'Positions must be sequential 1-{len(v)}, got {positions}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "matches": [
                        {
                            "teams": ("Liverpool", "Aston Villa"),
                            "position": 1,
                            "highlights_start": 112.0,
                            "highlights_end": 607.3,
                            "confidence": 0.95,
                            "detection_sources": ["scoreboard", "ft_graphic"]
                        }
                    ],
                    "strategy_results": {
                        "scoreboard": [("Liverpool", "Aston Villa"), ("Burnley", "Arsenal")],
                        "ft_graphic": [("Liverpool", "Aston Villa"), ("Burnley", "Arsenal")],
                        "mentions": [("Liverpool", "Aston Villa"), ("Burnley", "Arsenal")]
                    },
                    "consensus_confidence": 1.0,
                    "disagreements": []
                }
            ]
        }
    }


# Legacy compatibility: Export types for backward compatibility
__all__ = [
    'Scene',
    'TeamMatch',
    'OCRResult',
    'ProcessedScene',
    'BoundaryValidation',
    'MatchBoundary',
    'RunningOrderResult'
]
