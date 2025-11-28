"""Unit tests for cache validation logic in pipeline stages.

Tests cache invalidation for scene detection, team extraction, and transcription.
Uses tmp_path fixture for isolated file I/O testing.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ==================================================================================
# Test Class 1: Scene Detection Cache Validation
# ==================================================================================

class TestSceneDetectionCacheValidation:
    """Test cache validation logic in run_scene_detection()."""

    @pytest.fixture
    def video_path(self, tmp_path):
        """Create a dummy video file for testing."""
        video = tmp_path / "test_video.mp4"
        video.touch()
        return video

    @pytest.fixture
    def scene_cache_file(self, tmp_path):
        """Create a valid scene detection cache file."""
        cache_dir = tmp_path / "data" / "cache" / "test_video"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "scenes.json"

        cache_data = {
            "metadata": {
                "video_path": str(tmp_path / "test_video.mp4"),
                "video_name": "test_video",
                "processed_at": "2025-11-26T10:00:00Z",
                "detector_type": "content",
                "threshold": 30.0,
                "min_scene_duration": 0.5,
                "use_hybrid": True,
                "interval": 2.0,
                "dedupe_threshold": 1.0
            },
            "total_scenes": 100,
            "scenes": []
        }

        cache_file.write_text(json.dumps(cache_data, indent=2))
        return cache_file, cache_data

    @pytest.fixture
    def config(self, tmp_path):
        """Default config matching cache file."""
        return {
            "scene_detection": {
                "detector_type": "content",
                "threshold": 30.0,
                "min_scene_duration": 0.5
            },
            "ocr": {
                "sampling": {
                    "use_hybrid": True,
                    "interval": 2.0,
                    "dedupe_threshold": 1.0
                }
            },
            "cache": {
                "directory": str(tmp_path / "data" / "cache")
            }
        }

    def test_cache_hit_all_config_matches(self, video_path, scene_cache_file, config, tmp_path, monkeypatch):
        """Cache should be used when all config parameters match."""
        # Mock detect_scenes to ensure it's not called
        with patch('motd.__main__.detect_scenes') as mock_detect:
            # Change working directory to tmp_path
            monkeypatch.chdir(tmp_path)

            from motd.__main__ import run_scene_detection

            output, frames_dir, cache_was_used = run_scene_detection(
                video_path=video_path,
                config=config,
                output=scene_cache_file[0],
                force=False
            )

            assert cache_was_used is True
            mock_detect.assert_not_called()  # Should not re-detect

    @pytest.mark.parametrize("changed_param,new_value", [
        ("detector_type", "adaptive"),
        ("threshold", 25.0),
        ("min_scene_duration", 1.0),
        ("use_hybrid", False),
        ("interval", 5.0),
        ("dedupe_threshold", 2.0),
    ])
    def test_cache_miss_when_config_changes(self, video_path, scene_cache_file, config, tmp_path, monkeypatch, changed_param, new_value):
        """Cache should be invalidated when any config parameter changes."""
        # Modify config
        if changed_param in ["detector_type", "threshold", "min_scene_duration"]:
            config["scene_detection"][changed_param] = new_value
        else:
            config["ocr"]["sampling"][changed_param] = new_value

        # Mock detect_scenes and extract_key_frames to avoid actual processing
        with patch('motd.__main__.detect_scenes', return_value=[]):
            with patch('motd.__main__.extract_key_frames_for_scenes'):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_scene_detection

                output, frames_dir, cache_was_used = run_scene_detection(
                    video_path=video_path,
                    config=config,
                    output=scene_cache_file[0],
                    force=False
                )

                assert cache_was_used is False

    def test_corrupted_cache_file(self, video_path, scene_cache_file, config, tmp_path, monkeypatch):
        """Cache validation should fail gracefully on corrupted JSON."""
        # Corrupt cache file
        scene_cache_file[0].write_text("{invalid json")

        with patch('motd.__main__.detect_scenes', return_value=[]):
            with patch('motd.__main__.extract_key_frames_for_scenes'):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_scene_detection

                output, frames_dir, cache_was_used = run_scene_detection(
                    video_path=video_path,
                    config=config,
                    output=scene_cache_file[0],
                    force=False
                )

                assert cache_was_used is False

    def test_missing_metadata_section(self, video_path, scene_cache_file, config, tmp_path, monkeypatch):
        """Cache validation should fail when metadata section is missing."""
        # Remove metadata
        cache_data = {"total_scenes": 100, "scenes": []}
        scene_cache_file[0].write_text(json.dumps(cache_data))

        with patch('motd.__main__.detect_scenes', return_value=[]):
            with patch('motd.__main__.extract_key_frames_for_scenes'):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_scene_detection

                output, frames_dir, cache_was_used = run_scene_detection(
                    video_path=video_path,
                    config=config,
                    output=scene_cache_file[0],
                    force=False
                )

                assert cache_was_used is False

    def test_force_mode_bypasses_cache(self, video_path, scene_cache_file, config, tmp_path, monkeypatch):
        """Force mode should bypass cache even when valid."""
        with patch('motd.__main__.detect_scenes', return_value=[]):
            with patch('motd.__main__.extract_key_frames_for_scenes'):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_scene_detection

                output, frames_dir, cache_was_used = run_scene_detection(
                    video_path=video_path,
                    config=config,
                    output=scene_cache_file[0],
                    force=True  # Force mode
                )

                assert cache_was_used is False


# ==================================================================================
# Test Class 2: Team Extraction Cache Validation
# ==================================================================================

class TestTeamExtractionCacheValidation:
    """Test cache validation logic in run_team_extraction()."""

    @pytest.fixture
    def ocr_cache_file(self, tmp_path):
        """Create a valid OCR cache file."""
        cache_dir = tmp_path / "data" / "cache" / "test_episode"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "ocr_results.json"

        cache_data = {
            "metadata": {
                "episode_id": "test_episode",
                "processed_at": "2025-11-26T10:00:00Z",
                "ocr_library": "easyocr",
                "gpu": True,
                "confidence_threshold": 0.7
            },
            "total_scenes": 100,
            "ocr_results": []
        }

        cache_file.write_text(json.dumps(cache_data, indent=2))
        return cache_file, cache_data

    @pytest.fixture
    def scenes_file(self, tmp_path):
        """Create a valid scenes.json file."""
        scenes_file = tmp_path / "scenes.json"
        scenes_data = {
            "metadata": {"video_name": "test_episode"},
            "scenes": []
        }
        scenes_file.write_text(json.dumps(scenes_data))
        return scenes_file

    @pytest.fixture
    def config(self, tmp_path):
        """Default config matching cache file."""
        return {
            "ocr": {
                "library": "easyocr",
                "gpu": True,
                "confidence_threshold": 0.7
            },
            "cache": {
                "directory": str(tmp_path / "data" / "cache")
            }
        }

    def test_cache_hit_all_config_matches(self, scenes_file, ocr_cache_file, config, tmp_path, monkeypatch):
        """Cache should be used when all config parameters match."""
        # Mock ServiceFactory to avoid initializing real OCR components
        with patch('motd.__main__.ServiceFactory'):
            monkeypatch.chdir(tmp_path)

            from motd.__main__ import run_team_extraction

            output, cache_was_used = run_team_extraction(
                scenes_path=scenes_file,
                episode_id="test_episode",
                config=config,
                output=ocr_cache_file[0],
                force=False
            )

            assert cache_was_used is True

    @pytest.mark.parametrize("changed_param,new_value", [
        ("library", "paddleocr"),
        ("gpu", False),
        ("confidence_threshold", 0.8),
    ])
    def test_cache_miss_when_config_changes(self, scenes_file, ocr_cache_file, config, tmp_path, monkeypatch, changed_param, new_value):
        """Cache should be invalidated when any config parameter changes."""
        # Modify config
        config["ocr"][changed_param] = new_value

        # Mock all components to avoid actual OCR processing
        mock_summary = {
            'total_scenes_processed': 0,
            'unique_teams_detected': 0,
            'expected_teams_found': 0,
            'validated_detections': 0,
            'unexpected_detections': 0,
            'fixtures_identified': 0
        }

        with patch('motd.__main__.ServiceFactory') as mock_factory:
            with patch('motd.ocr.scene_processor.SceneProcessor'):
                with patch('motd.__main__.generate_summary', return_value=mock_summary):
                    monkeypatch.chdir(tmp_path)

                    from motd.__main__ import run_team_extraction

                    output, cache_was_used = run_team_extraction(
                        scenes_path=scenes_file,
                        episode_id="test_episode",
                        config=config,
                        output=ocr_cache_file[0],
                        force=False
                    )

                    assert cache_was_used is False

    def test_corrupted_cache_file(self, scenes_file, ocr_cache_file, config, tmp_path, monkeypatch):
        """Cache validation should fail gracefully on corrupted JSON."""
        # Corrupt cache file
        ocr_cache_file[0].write_text("{invalid json")

        mock_summary = {
            'total_scenes_processed': 0,
            'unique_teams_detected': 0,
            'expected_teams_found': 0,
            'validated_detections': 0,
            'unexpected_detections': 0,
            'fixtures_identified': 0
        }

        with patch('motd.__main__.ServiceFactory'):
            with patch('motd.ocr.scene_processor.SceneProcessor'):
                with patch('motd.__main__.generate_summary', return_value=mock_summary):
                    monkeypatch.chdir(tmp_path)

                    from motd.__main__ import run_team_extraction

                    output, cache_was_used = run_team_extraction(
                        scenes_path=scenes_file,
                        episode_id="test_episode",
                        config=config,
                        output=ocr_cache_file[0],
                        force=False
                    )

                    assert cache_was_used is False

    def test_force_mode_bypasses_cache(self, scenes_file, ocr_cache_file, config, tmp_path, monkeypatch):
        """Force mode should bypass cache even when valid."""
        mock_summary = {
            'total_scenes_processed': 0,
            'unique_teams_detected': 0,
            'expected_teams_found': 0,
            'validated_detections': 0,
            'unexpected_detections': 0,
            'fixtures_identified': 0
        }

        with patch('motd.__main__.ServiceFactory'):
            with patch('motd.ocr.scene_processor.SceneProcessor'):
                with patch('motd.__main__.generate_summary', return_value=mock_summary):
                    monkeypatch.chdir(tmp_path)

                    from motd.__main__ import run_team_extraction

                    output, cache_was_used = run_team_extraction(
                        scenes_path=scenes_file,
                        episode_id="test_episode",
                        config=config,
                        output=ocr_cache_file[0],
                        force=True  # Force mode
                    )

                    assert cache_was_used is False


# ==================================================================================
# Test Class 3: Transcription Cache Validation
# ==================================================================================

class TestTranscriptionCacheValidation:
    """Test cache validation logic in run_transcription()."""

    @pytest.fixture
    def video_path(self, tmp_path):
        """Create a dummy video file for testing."""
        video = tmp_path / "test_video.mp4"
        video.touch()
        return video

    @pytest.fixture
    def transcript_cache_file(self, tmp_path):
        """Create a valid transcript cache file."""
        cache_dir = tmp_path / "data" / "cache" / "test_video"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "transcript.json"

        cache_data = {
            "metadata": {
                "video_path": str(tmp_path / "test_video.mp4"),
                "model_size": "large-v3",
                "device": "cpu",
                "processed_at": "2025-11-26T10:00:00Z"
            },
            "language": "en",
            "duration": 5400.0,
            "segment_count": 200,
            "segments": []
        }

        cache_file.write_text(json.dumps(cache_data, indent=2))
        return cache_file, cache_data

    @pytest.fixture
    def config(self):
        """Default config matching cache file."""
        return {
            "transcription": {
                "model_size": "large-v3",
                "device": "auto"
            }
        }

    def test_cache_hit_all_config_matches(self, video_path, transcript_cache_file, config, tmp_path, monkeypatch):
        """Cache should be used when all config parameters match."""
        monkeypatch.chdir(tmp_path)

        from motd.__main__ import run_transcription

        output, cache_was_used = run_transcription(
            video_path=video_path,
            config=config,
            output=transcript_cache_file[0],
            force=False
        )

        assert cache_was_used is True

    def test_cache_miss_when_model_changes(self, video_path, transcript_cache_file, tmp_path, monkeypatch):
        """Cache should be invalidated when model_size changes."""
        config = {
            "transcription": {
                "model_size": "medium",  # Different from cache (large-v3)
                "device": "auto"
            }
        }

        # Mock AudioExtractor and WhisperTranscriber to avoid actual processing
        mock_extractor = MagicMock()
        mock_extractor.return_value.extract.return_value = {
            'output_size_mb': 100.0,
            'duration_seconds': 5400.0
        }

        mock_transcriber = MagicMock()
        mock_transcriber.return_value.transcribe.return_value = {
            'language': 'en',
            'duration': 5400.0,
            'segment_count': 200,
            'segments': []
        }
        mock_transcriber.return_value.device = 'cpu'

        with patch('motd.__main__.AudioExtractor', mock_extractor):
            with patch('motd.__main__.WhisperTranscriber', mock_transcriber):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_transcription

                output, cache_was_used = run_transcription(
                    video_path=video_path,
                    config=config,
                    output=transcript_cache_file[0],
                    force=False
                )

                assert cache_was_used is False

    def test_cache_miss_when_device_changes(self, video_path, transcript_cache_file, tmp_path, monkeypatch):
        """Cache should be invalidated when device changes (but not when device='auto')."""
        config = {
            "transcription": {
                "model_size": "large-v3",
                "device": "cuda"  # Different from cache (cpu), not auto
            }
        }

        mock_extractor = MagicMock()
        mock_extractor.return_value.extract.return_value = {
            'output_size_mb': 100.0,
            'duration_seconds': 5400.0
        }

        mock_transcriber = MagicMock()
        mock_transcriber.return_value.transcribe.return_value = {
            'language': 'en',
            'duration': 5400.0,
            'segment_count': 200,
            'segments': []
        }
        mock_transcriber.return_value.device = 'cuda'

        with patch('motd.__main__.AudioExtractor', mock_extractor):
            with patch('motd.__main__.WhisperTranscriber', mock_transcriber):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_transcription

                output, cache_was_used = run_transcription(
                    video_path=video_path,
                    config=config,
                    output=transcript_cache_file[0],
                    force=False
                )

                assert cache_was_used is False

    def test_auto_device_accepts_any_cached_device(self, video_path, transcript_cache_file, tmp_path, monkeypatch):
        """Device 'auto' should not invalidate cache regardless of cached device."""
        config = {
            "transcription": {
                "model_size": "large-v3",
                "device": "auto"  # Auto mode
            }
        }

        # Cache has device='cpu'
        assert transcript_cache_file[1]["metadata"]["device"] == "cpu"

        monkeypatch.chdir(tmp_path)

        from motd.__main__ import run_transcription

        output, cache_was_used = run_transcription(
            video_path=video_path,
            config=config,
            output=transcript_cache_file[0],
            force=False
        )

        # Should use cache (auto accepts any device)
        assert cache_was_used is True

    def test_force_mode_bypasses_cache(self, video_path, transcript_cache_file, config, tmp_path, monkeypatch):
        """Force mode should bypass cache even when valid."""
        mock_extractor = MagicMock()
        mock_extractor.return_value.extract.return_value = {
            'output_size_mb': 100.0,
            'duration_seconds': 5400.0
        }

        mock_transcriber = MagicMock()
        mock_transcriber.return_value.transcribe.return_value = {
            'language': 'en',
            'duration': 5400.0,
            'segment_count': 200,
            'segments': []
        }
        mock_transcriber.return_value.device = 'cpu'

        with patch('motd.__main__.AudioExtractor', mock_extractor):
            with patch('motd.__main__.WhisperTranscriber', mock_transcriber):
                monkeypatch.chdir(tmp_path)

                from motd.__main__ import run_transcription

                output, cache_was_used = run_transcription(
                    video_path=video_path,
                    config=config,
                    output=transcript_cache_file[0],
                    force=True  # Force mode
                )

                assert cache_was_used is False
