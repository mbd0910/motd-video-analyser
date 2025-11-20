#!/usr/bin/env python3
"""
Test SceneProcessor on scene 501 (frame_0834) to debug why it's rejected.

This mimics exactly what the pipeline does during team extraction.
"""

import sys
from pathlib import Path
import yaml
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motd.pipeline.models import Scene
from motd.ocr.reader import OCRReader
from motd.ocr.team_matcher import TeamMatcher
from motd.ocr.fixture_matcher import FixtureMatcher
from motd.ocr.scene_processor import SceneProcessor, EpisodeContext

# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Load episode manifest
with open('data/episodes/episode_manifest.json') as f:
    manifest = json.load(f)

episode_id = 'motd_2025-26_2025-11-08'
episode_data = next(e for e in manifest['episodes'] if e['episode_id'] == episode_id)

# Load scenes
with open(f'data/cache/{episode_id}/scenes.json') as f:
    scenes_data = json.load(f)

# Find scene 501
scene_dict = next(s for s in scenes_data['scenes'] if s['scene_id'] == 501)

print(f"Testing scene 501:")
print(f"  Duration: {scene_dict['duration']:.3f}s")
print(f"  Frames: {len(scene_dict['frames'])}")
print(f"  Frame: {Path(scene_dict['frames'][0]).name}")
print()

# Initialize components
print("Initializing OCR reader...")
ocr_reader = OCRReader(config['ocr'])

print("Initializing team matcher...")
teams_path = Path(config['teams']['path'])
team_matcher = TeamMatcher(teams_path)

print("Initializing fixture matcher...")
fixtures_path = Path(config['fixtures']['path'])
fixture_matcher = FixtureMatcher(fixtures_path, Path(config['episodes']['manifest_path']))

# Get expected fixtures for episode
expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)
expected_teams = list(set([f['home_team'] for f in expected_fixtures] + [f['away_team'] for f in expected_fixtures]))

print(f"Expected fixtures: {len(expected_fixtures)}")
print(f"Expected teams: {len(expected_teams)}")
print()

# Create episode context
context = EpisodeContext(
    episode_id=episode_id,
    expected_teams=expected_teams,
    expected_fixtures=expected_fixtures
)

# Create scene processor
processor = SceneProcessor(
    ocr_reader=ocr_reader,
    team_matcher=team_matcher,
    fixture_matcher=fixture_matcher,
    context=context
)

# Convert scene dict to Scene model
scene = Scene(
    scene_number=scene_dict['scene_id'],
    start_time=scene_dict['start_time'],
    start_seconds=scene_dict['start_seconds'],
    end_seconds=scene_dict['end_seconds'],
    duration=scene_dict['duration'],
    frames=scene_dict.get('frames', []),
    key_frame_path=scene_dict.get('key_frame_path')
)

print("Processing scene 501...")
print("=" * 80)

# Enable DEBUG logging temporarily
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Process scene
result = processor.process(scene)

print("=" * 80)
if result:
    print(f"✅ SUCCESS!")
    print(f"  Teams: {result.team1} vs {result.team2}")
    print(f"  OCR source: {result.ocr_source}")
    print(f"  Confidence: {result.match_confidence}")
    print(f"  Fixture: {result.fixture_id}")
else:
    print(f"❌ FAILED - Scene 501 returned None")
    print()
    print("This explains why frame_0834 is not in ocr_results.json!")
