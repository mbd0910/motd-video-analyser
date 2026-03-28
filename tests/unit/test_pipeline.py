"""Tests for the pipeline orchestrator module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from motd.models import (
    EpisodeAnalysis,
    Fixture,
    MatchCoverage,
    Score,
    Segment,
    Transcript,
    TranscriptSegment,
)
from motd.pipeline import PipelineError, run

EPISODE_ID = "motd_2025-26_2025-11-01"
BROADCAST_DATE = "2025-11-01"
SEASON = "2025-26"

SAMPLE_TRANSCRIPT = Transcript(
    episode_id=EPISODE_ID,
    duration_seconds=5400.0,
    segments=[
        TranscriptSegment(start=0.0, end=10.0, text="Welcome to Match of the Day."),
        TranscriptSegment(start=10.0, end=60.0, text="First up, Arsenal versus Chelsea."),
    ],
)

SAMPLE_FIXTURES = [
    Fixture(
        match_id="2025-11-01-arsenal-chelsea",
        date="2025-11-01",
        home_team="Arsenal",
        away_team="Chelsea",
        venue="Emirates Stadium",
        score=Score(home=3, away=1),
    ),
]

SAMPLE_ANALYSIS = EpisodeAnalysis(
    episode_id=EPISODE_ID,
    broadcast_date=BROADCAST_DATE,
    season=SEASON,
    matches=[
        MatchCoverage(
            order=1,
            home_team="Arsenal",
            away_team="Chelsea",
            venue="Emirates Stadium",
            score=Score(home=3, away=1),
            segments={"highlights": Segment(start="00:10", end="10:00")},
        ),
    ],
)


class TestPipelineFromVideoPath:
    """Pipeline run with a local video path (no download)."""

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_runs_all_stages(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(video_path=str(video), cache_dir=str(tmp_path / "cache"))

        mock_transcribe.assert_called_once()
        mock_analyse.assert_called_once()
        mock_publish.assert_called_once()

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_derives_episode_id_from_filename(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(video_path=str(video), cache_dir=str(tmp_path / "cache"))

        # Transcribe should receive the episode_id derived from the filename
        args = mock_transcribe.call_args
        assert args[1]["episode_id"] == EPISODE_ID

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_explicit_episode_id_overrides_filename(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / "some_video.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(video_path=str(video), episode_id=EPISODE_ID,
            cache_dir=str(tmp_path / "cache"))

        args = mock_transcribe.call_args
        assert args[1]["episode_id"] == EPISODE_ID


class TestPipelineFromUrl:
    """Pipeline run with an iPlayer URL (triggers download)."""

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    @patch("motd.pipeline._do_download")
    def test_download_then_full_pipeline(
        self, mock_download: MagicMock, mock_transcribe: MagicMock,
        mock_fixtures: MagicMock, mock_analyse: MagicMock,
        mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_download.return_value = (str(video), EPISODE_ID)
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(url="https://www.bbc.co.uk/iplayer/episode/m00test",
            cache_dir=str(tmp_path / "cache"))

        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()
        mock_analyse.assert_called_once()
        mock_publish.assert_called_once()


class TestPipelineValidation:
    """Input validation."""

    def test_no_video_or_url_raises(self) -> None:
        with pytest.raises(PipelineError, match="video_path.*url"):
            run()

    def test_skip_to_without_episode_id_raises(self) -> None:
        with pytest.raises(PipelineError, match="episode.id"):
            run(skip_to="analyse")


class TestPipelineSkipTo:
    """--skip-to flag for resuming from a specific stage."""

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_skip_to_analyse_skips_transcribe(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        # Set up cached transcript
        cache_dir = tmp_path / "cache" / EPISODE_ID
        cache_dir.mkdir(parents=True)
        transcript_path = cache_dir / "transcript.json"
        transcript_path.write_text(SAMPLE_TRANSCRIPT.model_dump_json())

        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(
            episode_id=EPISODE_ID,
            skip_to="analyse",
            cache_dir=str(tmp_path / "cache"),
        )

        mock_transcribe.assert_not_called()
        mock_analyse.assert_called_once()
        mock_publish.assert_called_once()

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._do_transcribe")
    def test_skip_to_publish_skips_transcribe_and_analyse(
        self, mock_transcribe: MagicMock, mock_analyse: MagicMock,
        mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        # Set up cached analysis
        cache_dir = tmp_path / "cache" / EPISODE_ID
        cache_dir.mkdir(parents=True)
        analysis_path = cache_dir / "analysis.json"
        analysis_path.write_text(SAMPLE_ANALYSIS.model_dump_json())

        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(
            episode_id=EPISODE_ID,
            skip_to="publish",
            cache_dir=str(tmp_path / "cache"),
        )

        mock_transcribe.assert_not_called()
        mock_analyse.assert_not_called()
        mock_publish.assert_called_once()


class TestPipelineErrorHandling:
    """Error handling preserves completed stage outputs."""

    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_analysis_failure_preserves_transcript(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.side_effect = RuntimeError("Claude failed")

        cache_dir = tmp_path / "cache"

        with pytest.raises(RuntimeError, match="Claude failed"):
            run(video_path=str(video), cache_dir=str(cache_dir))

        # Transcript should have been cached before analysis failed
        transcript_path = cache_dir / EPISODE_ID / "transcript.json"
        assert transcript_path.exists()

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_publish_failure_preserves_analysis(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.side_effect = RuntimeError("R2 upload failed")

        cache_dir = tmp_path / "cache"

        with pytest.raises(RuntimeError, match="R2 upload failed"):
            run(video_path=str(video), cache_dir=str(cache_dir))

        # Analysis should have been cached before publish failed
        analysis_path = cache_dir / EPISODE_ID / "analysis.json"
        assert analysis_path.exists()


class TestPipelineCaching:
    """Caching behaviour — skip expensive stages when cached."""

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_cached_transcript_skips_transcription(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()

        # Pre-populate cached transcript
        cache_dir = tmp_path / "cache"
        ep_cache = cache_dir / EPISODE_ID
        ep_cache.mkdir(parents=True)
        (ep_cache / "transcript.json").write_text(
            SAMPLE_TRANSCRIPT.model_dump_json()
        )

        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(video_path=str(video), cache_dir=str(cache_dir))

        mock_transcribe.assert_not_called()
        mock_analyse.assert_called_once()

    @patch("motd.pipeline._do_publish")
    @patch("motd.pipeline._do_analyse")
    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_force_ignores_cache(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        mock_analyse: MagicMock, mock_publish: MagicMock, tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()

        # Pre-populate cached transcript
        cache_dir = tmp_path / "cache"
        ep_cache = cache_dir / EPISODE_ID
        ep_cache.mkdir(parents=True)
        (ep_cache / "transcript.json").write_text(
            SAMPLE_TRANSCRIPT.model_dump_json()
        )

        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = SAMPLE_FIXTURES
        mock_analyse.return_value = SAMPLE_ANALYSIS
        mock_publish.return_value = f"episodes/{EPISODE_ID}.json"

        run(video_path=str(video), cache_dir=str(cache_dir), force=True)

        mock_transcribe.assert_called_once()


class TestPipelineNoFixtures:
    """Non-PL episode (no matching fixtures) should fail clearly."""

    @patch("motd.pipeline._load_fixtures")
    @patch("motd.pipeline._do_transcribe")
    def test_no_fixtures_raises(
        self, mock_transcribe: MagicMock, mock_fixtures: MagicMock,
        tmp_path: Path,
    ) -> None:
        video = tmp_path / f"{EPISODE_ID}.mp4"
        video.touch()
        mock_transcribe.return_value = SAMPLE_TRANSCRIPT
        mock_fixtures.return_value = []

        with pytest.raises(PipelineError, match="[Nn]o.*fixtures"):
            run(video_path=str(video), cache_dir=str(tmp_path / "cache"))
