"""
Debug script for frame_2214 (Brighton vs Leeds) - the only failing frame.

Runs SceneProcessor with DEBUG logging to identify rejection point.
"""

import logging
from pathlib import Path
import yaml

from src.motd.pipeline.factory import ServiceFactory
from src.motd.pipeline.models import Scene

# Set up DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load config
config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Create scene processor
factory = ServiceFactory(config)
episode_id = "motd_2025-26_2025-11-01"
processor = factory.create_scene_processor(episode_id)

# Test frame
frame_path = Path(__file__).parent / "fixtures" / "ft_graphics" / "frame_2214_interval_sampling_4300.0s.jpg"

print(f"\n{'='*80}")
print(f"DEBUGGING frame_2214: Brighton & Hove Albion vs Leeds United")
print(f"Frame: {frame_path}")
print(f"Exists: {frame_path.exists()}")
print(f"{'='*80}\n")

# Create scene
scene = Scene(
    scene_number=2214,
    start_time="71:40",
    start_seconds=4300.0,
    end_seconds=4301.0,
    duration=1.0,
    frames=[str(frame_path)]
)

# Process with DEBUG logging
result = processor.process(scene)

print(f"\n{'='*80}")
print(f"RESULT:")
print(f"{'='*80}")
if result:
    print(f"✅ DETECTED!")
    print(f"  Teams: {result.team1} vs {result.team2}")
    print(f"  Home/Away: {result.home_team} vs {result.away_team}")
    print(f"  Confidence: {result.match_confidence:.2f}")
    print(f"  OCR Source: {result.ocr_source}")
    print(f"  Fixture ID: {result.fixture_id}")
else:
    print(f"❌ REJECTED - Scene returned None")
    print(f"\nCheck DEBUG logs above to identify rejection point.")
print(f"{'='*80}\n")
