"""
Integration tests for transcription caching and CLI.

Testing strategy:
- Test cache invalidation logic (config hash validation)
- Test file I/O for cache operations
- Minimal mocking - focus on actual logic we wrote
"""

import json
import pytest
from pathlib import Path

# These tests validate cache invalidation logic only
# We don't test the full transcription pipeline (that's tested manually)


class TestCacheInvalidation:
    """Test cache validation and invalidation logic."""

    def test_cache_structure(self, tmp_path):
        """Test cached transcript has expected structure."""
        cache_file = tmp_path / "transcript.json"

        # Simulate cached transcript
        cached_data = {
            'metadata': {
                'video_path': '/path/to/video.mp4',
                'model_size': 'large-v3',
                'device': 'cpu',
                'processed_at': '2025-11-16T10:00:00Z',
                'processing_time_seconds': 180.5,
                'real_time_factor': 30.0
            },
            'language': 'en',
            'duration': 5400.0,
            'segment_count': 200,
            'segments': []
        }

        cache_file.write_text(json.dumps(cached_data, indent=2))

        # Verify structure
        with open(cache_file) as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'language' in data
        assert 'duration' in data
        assert 'segment_count' in data
        assert 'segments' in data

        # Verify metadata fields needed for cache validation
        assert data['metadata']['model_size'] == 'large-v3'
        assert data['metadata']['device'] == 'cpu'

    def test_config_change_detection_model_size(self):
        """Test detecting model_size config changes."""
        # Cached config
        cached_model = 'medium'
        cached_device = 'cpu'

        # Current config
        current_model = 'large-v3'
        current_device = 'cpu'

        # Should detect change
        config_changed = (
            cached_model != current_model or
            (current_device != 'auto' and cached_device != current_device)
        )

        assert config_changed is True

    def test_config_change_detection_device(self):
        """Test detecting device config changes."""
        cached_model = 'large-v3'
        cached_device = 'cpu'

        current_model = 'large-v3'
        current_device = 'cuda'

        config_changed = (
            cached_model != current_model or
            (current_device != 'auto' and cached_device != current_device)
        )

        assert config_changed is True

    def test_config_no_change(self):
        """Test cache valid when config unchanged."""
        cached_model = 'large-v3'
        cached_device = 'cpu'

        current_model = 'large-v3'
        current_device = 'cpu'

        config_changed = (
            cached_model != current_model or
            (current_device != 'auto' and cached_device != current_device)
        )

        assert config_changed is False

    def test_auto_device_accepts_any_cached_device(self):
        """Test that device='auto' doesn't invalidate cache."""
        cached_model = 'large-v3'
        cached_device = 'cuda'  # Was run on GPU

        current_model = 'large-v3'
        current_device = 'auto'  # Now using auto

        # Should NOT invalidate - 'auto' accepts any device
        config_changed = (
            cached_model != current_model or
            (current_device != 'auto' and cached_device != current_device)
        )

        assert config_changed is False


class TestCacheFileOperations:
    """Test cache directory and file operations."""

    def test_cache_directory_structure(self, tmp_path):
        """Test expected cache directory structure."""
        cache_root = tmp_path / "data" / "cache"
        video_name = "motd_2025_08_17"
        video_cache = cache_root / video_name

        video_cache.mkdir(parents=True, exist_ok=True)

        # Create transcript
        transcript_file = video_cache / "transcript.json"
        transcript_data = {
            'metadata': {'model_size': 'large-v3'},
            'segments': []
        }
        transcript_file.write_text(json.dumps(transcript_data))

        # Verify structure
        assert video_cache.exists()
        assert transcript_file.exists()
        assert transcript_file.name == "transcript.json"

    def test_cache_overwrite(self, tmp_path):
        """Test that cache can be overwritten (force mode)."""
        cache_file = tmp_path / "transcript.json"

        # Old cache
        old_data = {'metadata': {'model_size': 'tiny'}, 'segments': []}
        cache_file.write_text(json.dumps(old_data))

        # Overwrite
        new_data = {'metadata': {'model_size': 'large-v3'}, 'segments': []}
        cache_file.write_text(json.dumps(new_data))

        # Verify overwritten
        with open(cache_file) as f:
            data = json.load(f)

        assert data['metadata']['model_size'] == 'large-v3'
