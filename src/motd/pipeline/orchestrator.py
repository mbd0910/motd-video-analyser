"""Pipeline orchestrator for running the full MOTD analysis workflow."""

import logging
import time
from pathlib import Path
from typing import Any

from motd.llm.prompt_builder import BuiltPrompt


class PipelineOrchestrator:
    """
    Orchestrates the full MOTD analysis pipeline with smart caching.

    Manages 4 sequential stages:
    1. Scene Detection (video → scenes.json + frames/)
    2. Team Extraction (scenes.json → ocr_results.json)
    3. Transcription (video → transcript.json)
    4. LLM Prompt Generation (→ transcript_for_llm.txt)

    Features:
    - Smart cache validation (skip completed stages if config unchanged)
    - Fail-fast error handling (exception stops pipeline)
    - Stage-level progress indication (start/complete/skip messages)
    - Force mode bypasses cache for all stages
    """

    def __init__(
        self,
        video_path: Path,
        config: dict[str, Any],
        force: bool = False
    ):
        """
        Initialize orchestrator.

        Args:
            video_path: Path to MOTD video file
            config: Configuration dictionary from config.yaml
            force: Force full pipeline run, ignoring cache
        """
        self.video_path = video_path
        self.config = config
        self.force = force
        self.episode_id = video_path.stem

        # Setup cache directory
        cache_config = config.get("cache", {})
        cache_dir = Path(cache_config.get("directory", "data/cache"))
        self.cache_dir = cache_dir / self.episode_id

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Orchestrator initialized for episode: {self.episode_id}")
        self.logger.info(f"Video: {video_path}")
        self.logger.info(f"Force mode: {force}")

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds as 'Xm Ys' string."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    def run_pipeline(self) -> tuple[BuiltPrompt, Path]:
        """
        Execute the full pipeline sequentially.

        Returns:
            Tuple of (BuiltPrompt with LLM prompt stats, output path)

        Raises:
            Exception: Any stage failure raises exception (fail-fast)
        """
        pipeline_start_time = time.time()

        print(f"\n{'='*70}")
        print(f"  MOTD Pipeline - Episode: {self.episode_id}")
        print(f"{'='*70}\n")

        # Stage 1: Scene Detection
        scenes_path, frames_dir = self._run_stage_1_scene_detection()

        # Stage 2: Team Extraction
        ocr_path = self._run_stage_2_team_extraction(scenes_path)

        # Stage 3: Transcription
        transcript_path = self._run_stage_3_transcription()

        # Stage 4: LLM Prompt Generation
        result, output_path = self._run_stage_4_llm_prompt()

        # Pipeline complete
        pipeline_duration = time.time() - pipeline_start_time

        print(f"\n{'='*70}")
        print(f"  Pipeline complete! Total time: {self._format_duration(pipeline_duration)}")
        print(f"{'='*70}\n")

        self.logger.info(f"Pipeline completed successfully in {pipeline_duration:.1f}s")

        return result, output_path

    def _run_stage_1_scene_detection(self) -> tuple[Path, Path]:
        """
        Stage 1: Detect scenes and extract frames.

        Returns:
            Tuple of (scenes.json path, frames directory path)
        """
        from motd.__main__ import run_scene_detection

        print("▶ Stage 1/4: Scene Detection starting...")
        stage_start = time.time()

        try:
            scenes_path, frames_dir, cache_was_used = run_scene_detection(
                video_path=self.video_path,
                config=self.config,
                force=self.force
            )

            stage_duration = time.time() - stage_start

            # Use explicit cache status instead of timing heuristic
            if cache_was_used:
                print(f"⊘ Stage 1/4: Scene Detection skipped (cache valid)\n")
            else:
                print(f"✓ Stage 1/4: Scene Detection complete ({self._format_duration(stage_duration)})\n")

            self.logger.info(f"Stage 1 completed in {stage_duration:.1f}s (cache: {cache_was_used})")
            return scenes_path, frames_dir

        except Exception as e:
            self.logger.error(f"Stage 1 failed: {e}", exc_info=True)
            print(f"\n❌ Stage 1/4: Scene Detection FAILED")
            print(f"   Error: {e}")
            print(f"\n   To resume, run: motd run {self.video_path}")
            raise

    def _run_stage_2_team_extraction(self, scenes_path: Path) -> Path:
        """
        Stage 2: Extract teams via OCR.

        Args:
            scenes_path: Path to scenes.json from Stage 1

        Returns:
            Path to ocr_results.json
        """
        from motd.__main__ import run_team_extraction

        print("▶ Stage 2/4: Team Extraction starting...")
        stage_start = time.time()

        try:
            ocr_path, cache_was_used = run_team_extraction(
                scenes_path=scenes_path,
                episode_id=self.episode_id,
                config=self.config,
                force=self.force
            )

            stage_duration = time.time() - stage_start

            # Use explicit cache status instead of timing heuristic
            if cache_was_used:
                print(f"⊘ Stage 2/4: Team Extraction skipped (cache valid)\n")
            else:
                print(f"✓ Stage 2/4: Team Extraction complete ({self._format_duration(stage_duration)})\n")

            self.logger.info(f"Stage 2 completed in {stage_duration:.1f}s (cache: {cache_was_used})")
            return ocr_path

        except Exception as e:
            self.logger.error(f"Stage 2 failed: {e}", exc_info=True)
            print(f"\n❌ Stage 2/4: Team Extraction FAILED")
            print(f"   Error: {e}")
            print(f"\n   To resume, run: motd run {self.video_path}")
            raise

    def _run_stage_3_transcription(self) -> Path:
        """
        Stage 3: Transcribe audio via Whisper.

        Returns:
            Path to transcript.json
        """
        from motd.__main__ import run_transcription

        print("▶ Stage 3/4: Transcription starting...")
        stage_start = time.time()

        try:
            transcript_path, cache_was_used = run_transcription(
                video_path=self.video_path,
                config=self.config,
                force=self.force
            )

            stage_duration = time.time() - stage_start

            # Use explicit cache status instead of timing heuristic
            if cache_was_used:
                print(f"⊘ Stage 3/4: Transcription skipped (cache valid)\n")
            else:
                print(f"✓ Stage 3/4: Transcription complete ({self._format_duration(stage_duration)})\n")

            self.logger.info(f"Stage 3 completed in {stage_duration:.1f}s (cache: {cache_was_used})")
            return transcript_path

        except Exception as e:
            self.logger.error(f"Stage 3 failed: {e}", exc_info=True)
            print(f"\n❌ Stage 3/4: Transcription FAILED")
            print(f"   Error: {e}")
            print(f"\n   To resume, run: motd run {self.video_path}")
            raise

    def _run_stage_4_llm_prompt(self) -> tuple[BuiltPrompt, Path]:
        """
        Stage 4: Generate LLM prompt for episode analysis.

        Returns:
            Tuple of (BuiltPrompt result, output path)
        """
        from motd.__main__ import run_llm_prompt_generation

        print("▶ Stage 4/4: LLM Prompt Generation starting...")
        stage_start = time.time()

        try:
            result, output_path, cache_was_used = run_llm_prompt_generation(
                episode_id=self.episode_id,
                include_hints=True,
                force=self.force
            )

            stage_duration = time.time() - stage_start

            if cache_was_used:
                print(f"⊘ Stage 4/4: LLM Prompt Generation skipped (file exists)\n")
                self.logger.info(f"Stage 4 skipped (cache valid)")
            else:
                print(f"✓ Stage 4/4: LLM Prompt Generation complete ({int(stage_duration)}s)\n")
                self.logger.info(f"Stage 4 completed in {stage_duration:.1f}s")

            return result, output_path

        except Exception as e:
            self.logger.error(f"Stage 4 failed: {e}", exc_info=True)
            print(f"\n❌ Stage 4/4: LLM Prompt Generation FAILED")
            print(f"   Error: {e}")

            # Check if it's a missing dependency error
            if "No such file" in str(e) or "not found" in str(e).lower():
                print(f"\n   Possible causes:")
                print(f"   - Missing transcript.json (Stage 3 incomplete)")
                print(f"   - Missing episode_manifest.json")

            print(f"\n   To resume, run: motd run {self.video_path}")
            raise
