# MOTD Analyser - Implementation Roadmap

This document outlines a phased approach to building the MOTD Analyser, with clear milestones, validation checkpoints, and decision points.

---

## Philosophy

**Build → Validate → Iterate**

Each phase produces a working artifact that you can validate manually before proceeding. This approach:
- Catches issues early (before compounding)
- Builds confidence in the pipeline incrementally
- Allows you to learn and adjust as you go
- Provides natural blog post milestones

---

## Phase 0: Project Setup (Est. 1-2 hours)

### Goals
- Set up Python environment
- Install dependencies
- Create project structure
- Verify all tools work

### Tasks

#### 0.1 Environment Setup
```bash
# Set Python version
asdf local python 3.12.7  # or your preferred version manager

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### 0.2 Install System Dependencies
```bash
# Install ffmpeg
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### 0.3 Create Project Structure
```bash
mkdir -p src/motd_analyzer/{scene_detection,ocr,transcription,analysis,validation,pipeline,utils}
mkdir -p data/{teams,videos,cache,output}
mkdir -p config tests logs
touch src/motd_analyzer/__init__.py
touch src/motd_analyzer/__main__.py
```

#### 0.4 Install Python Dependencies
Create `requirements.txt`:
```
# Core
opencv-python==4.8.1
numpy==1.24.3
pyyaml==6.0.1

# Scene Detection
scenedetect[opencv]==0.6.2

# OCR
easyocr==1.7.0
torch==2.1.0

# Transcription
faster-whisper==0.9.0  # Note: Using faster-whisper instead of openai-whisper
# openai-whisper==20231117  # Alternative if faster-whisper has issues

# Testing
pytest==7.4.3
pytest-cov==4.1.0
```

Install:
```bash
pip install -r requirements.txt
```

#### 0.5 Create Team Names File
Create `data/teams/premier_league_2025_26.json`:
```json
{
  "teams": [
    {
      "full": "Arsenal",
      "abbrev": "Arsenal",
      "code": "ARS",
      "alternates": ["The Gunners", "Gunners"]
    },
    {
      "full": "Aston Villa",
      "abbrev": "Aston Villa",
      "code": "AVL",
      "alternates": ["Villa"]
    },
    {
      "full": "Bournemouth",
      "abbrev": "Bournemouth",
      "code": "BOU",
      "alternates": ["The Cherries", "Cherries"]
    },
    {
      "full": "Brentford",
      "abbrev": "Brentford",
      "code": "BRE",
      "alternates": ["The Bees", "Bees"]
    },
    {
      "full": "Brighton & Hove Albion",
      "abbrev": "Brighton",
      "code": "BHA",
      "alternates": ["Brighton", "The Seagulls", "Seagulls"]
    },
    {
      "full": "Chelsea",
      "abbrev": "Chelsea",
      "code": "CHE",
      "alternates": ["The Blues", "Blues"]
    },
    {
      "full": "Crystal Palace",
      "abbrev": "Crystal Palace",
      "code": "CRY",
      "alternates": ["Palace", "The Eagles", "Eagles"]
    },
    {
      "full": "Everton",
      "abbrev": "Everton",
      "code": "EVE",
      "alternates": ["The Toffees", "Toffees"]
    },
    {
      "full": "Fulham",
      "abbrev": "Fulham",
      "code": "FUL",
      "alternates": ["The Cottagers", "Cottagers"]
    },
    {
      "full": "Ipswich Town",
      "abbrev": "Ipswich",
      "code": "IPS",
      "alternates": ["Ipswich", "The Tractor Boys", "Tractor Boys"]
    },
    {
      "full": "Leicester City",
      "abbrev": "Leicester",
      "code": "LEI",
      "alternates": ["Leicester", "The Foxes", "Foxes"]
    },
    {
      "full": "Liverpool",
      "abbrev": "Liverpool",
      "code": "LIV",
      "alternates": ["The Reds", "Reds"]
    },
    {
      "full": "Manchester City",
      "abbrev": "Man City",
      "code": "MCI",
      "alternates": ["Man City", "City", "The Citizens", "Citizens"]
    },
    {
      "full": "Manchester United",
      "abbrev": "Man Utd",
      "code": "MUN",
      "alternates": ["Man Utd", "Man United", "United", "The Red Devils", "Red Devils"]
    },
    {
      "full": "Newcastle United",
      "abbrev": "Newcastle",
      "code": "NEW",
      "alternates": ["Newcastle", "The Magpies", "Magpies"]
    },
    {
      "full": "Nottingham Forest",
      "abbrev": "Nott'm Forest",
      "code": "NFO",
      "alternates": ["Forest", "Nottm Forest", "Notts Forest"]
    },
    {
      "full": "Southampton",
      "abbrev": "Southampton",
      "code": "SOU",
      "alternates": ["Saints", "The Saints"]
    },
    {
      "full": "Tottenham Hotspur",
      "abbrev": "Tottenham",
      "code": "TOT",
      "alternates": ["Spurs", "Tottenham", "The Lilywhites"]
    },
    {
      "full": "West Ham United",
      "abbrev": "West Ham",
      "code": "WHU",
      "alternates": ["West Ham", "The Hammers", "Hammers"]
    },
    {
      "full": "Wolverhampton Wanderers",
      "abbrev": "Wolves",
      "code": "WOL",
      "alternates": ["Wolves", "Wanderers"]
    }
  ]
}
```

#### 0.6 Create Fixtures and Episode Manifest Files

Create `data/fixtures/premier_league_2025_26.json`:
```json
{
  "season": "2025-26",
  "competition": "Premier League",
  "gameweeks": [
    {
      "gameweek": 1,
      "matches": [
        {
          "match_id": "2025-08-16-manutd-fulham",
          "date": "2025-08-16",
          "home_team": "Manchester United",
          "away_team": "Fulham",
          "kickoff": "20:00",
          "final_score": {"home": 1, "away": 0}
        },
        {
          "match_id": "2025-08-17-arsenal-wolves",
          "date": "2025-08-17",
          "home_team": "Arsenal",
          "away_team": "Wolverhampton Wanderers",
          "kickoff": "15:00",
          "final_score": {"home": 2, "away": 0}
        }
        // ... add remaining fixtures for gameweeks you're analyzing
      ]
    }
  ]
}
```

Create `data/episodes/episode_manifest.json`:
```json
{
  "episodes": [
    {
      "episode_id": "motd-2025-08-17",
      "video_filename": "MOTD_2025_08_17_S57E01.mp4",
      "video_source_url": "https://www.bbc.co.uk/iplayer/episode/...",
      "broadcast_date": "2025-08-17",
      "gameweek": 1,
      "expected_matches": [
        "2025-08-16-manutd-fulham",
        "2025-08-17-arsenal-wolves"
        // ... list all match_ids expected in this episode
      ],
      "duration": "01:22:45",
      "notes": "Opening weekend, Season 57 Episode 1"
    }
  ]
}
```

**Note**: You'll populate these files manually before processing videos. The fixture data limits team detection to expected matches, significantly improving OCR accuracy.

#### 0.7 Create Basic Config
Create `config/config.yaml`:
```yaml
scene_detection:
  threshold: 30.0
  min_scene_duration: 3.0

ocr:
  library: easyocr
  languages: ['en']
  gpu: true
  confidence_threshold: 0.7

transcription:
  model: large-v3
  language: en
  device: auto
  word_timestamps: true

teams:
  path: data/teams/premier_league_2025_26.json

cache:
  enabled: true
  directory: data/cache

output:
  directory: data/output
  format: json
  indent: 2

logging:
  level: INFO
  file: logs/pipeline.log
  console: true
```

### Validation Checkpoint
- [ ] Python environment activated
- [ ] `ffmpeg -version` works
- [ ] `pip list` shows all required packages
- [ ] Project structure created
- [ ] Team names JSON is valid
- [ ] Config YAML is valid

### Estimated Time: 1-2 hours

---

## Phase 1: Scene Detection (Est. 4-6 hours)

### Goals
- Detect scene transitions in a single MOTD episode
- Extract key frames at transition points
- Output timestamps to JSON
- Manually validate results

### Tasks

#### 1.1 Implement Scene Detector
Create `src/motd_analyzer/scene_detection/detector.py`:
```python
from scenedetect import detect, ContentDetector
import json

def detect_scenes(video_path, threshold=30.0, min_duration=3.0):
    """
    Detect scene transitions in video.

    Args:
        video_path: Path to video file
        threshold: Scene detection sensitivity (lower = more sensitive)
        min_duration: Minimum scene length in seconds

    Returns:
        List of scenes with start/end timestamps
    """
    detector = ContentDetector(threshold=threshold, min_scene_len=min_duration)
    scenes = detect(video_path, detector)

    results = []
    for i, (start, end) in enumerate(scenes):
        results.append({
            "scene_id": i + 1,
            "start_time": start.get_timecode(),
            "end_time": end.get_timecode(),
            "start_frame": start.get_frames(),
            "end_frame": end.get_frames(),
            "duration_seconds": (end - start).get_seconds()
        })

    return results
```

#### 1.2 Implement Frame Extractor
Create `src/motd_analyzer/scene_detection/frame_extractor.py`:
```python
import cv2
import os

def extract_key_frame(video_path, timestamp_seconds, output_path):
    """Extract a single frame at given timestamp."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)

    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_path, frame)

    cap.release()
    return ret

def extract_key_frames_for_scenes(video_path, scenes, output_dir):
    """Extract key frame for each scene."""
    os.makedirs(output_dir, exist_ok=True)

    for scene in scenes:
        frame_path = os.path.join(output_dir, f"scene_{scene['scene_id']:03d}.jpg")
        # Extract frame at start of scene
        extract_key_frame(video_path, scene['start_frame'] / 30.0, frame_path)
        scene['key_frame_path'] = frame_path
```

#### 1.3 Create CLI for Scene Detection
Add to `src/motd_analyzer/__main__.py`:
```python
import argparse
from motd_analyzer.scene_detection.detector import detect_scenes
from motd_analyzer.scene_detection.frame_extractor import extract_key_frames_for_scenes
import json

def main():
    parser = argparse.ArgumentParser(description='MOTD Analyser')
    parser.add_argument('command', choices=['detect-scenes'])
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--output', help='Output JSON path')
    parser.add_argument('--threshold', type=float, default=30.0)

    args = parser.parse_args()

    if args.command == 'detect-scenes':
        print(f"Detecting scenes in {args.video}...")
        scenes = detect_scenes(args.video, threshold=args.threshold)

        # Extract key frames
        episode_id = os.path.basename(args.video).replace('.mp4', '')
        frames_dir = f"data/cache/{episode_id}/frames"
        extract_key_frames_for_scenes(args.video, scenes, frames_dir)

        # Save results
        output = {
            "video_path": args.video,
            "total_scenes": len(scenes),
            "scenes": scenes
        }

        output_path = args.output or f"data/cache/{episode_id}/scenes.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Detected {len(scenes)} scenes. Results saved to {output_path}")

if __name__ == '__main__':
    main()
```

#### 1.4 Test on Sample Video
```bash
# Run scene detection on first video
python -m motd_analyzer detect-scenes data/videos/motd_2024_08_17.mp4

# This will create:
# - data/cache/motd_2024_08_17/scenes.json
# - data/cache/motd_2024_08_17/frames/scene_001.jpg ... scene_NNN.jpg
```

#### 1.5 Manual Validation
1. Open `data/cache/motd_2024_08_17/scenes.json`
2. Look at timestamps
3. Open corresponding frame images in `frames/`
4. Check: Do the detected scenes correspond to actual transitions?
5. Adjust `threshold` parameter if needed (lower = more sensitive)

### Validation Checkpoint
- [ ] Scene detection runs without errors
- [ ] JSON output is well-formed
- [ ] Key frames are extracted successfully
- [ ] Detected scenes match actual transitions (spot-check 10-20 scenes)
- [ ] No major transitions are missed
- [ ] Not too many false positives (every camera angle change detected)

### Success Criteria
- 40-80 scenes detected for a 90-minute episode (typical)
- Major transitions captured (studio ↔ highlights ↔ interviews)

### Estimated Time: 4-6 hours (including testing and validation)

---

## Phase 2: OCR & Team Detection (Est. 6-8 hours)

### Goals
- Extract text from key frames using EasyOCR
- Match extracted text to team names
- Identify which teams are in each match segment

### Tasks

#### 2.1 Implement OCR Reader
Create `src/motd_analyzer/ocr/reader.py`:
```python
import easyocr
import cv2

class OCRReader:
    def __init__(self, languages=['en'], gpu=True):
        self.reader = easyocr.Reader(languages, gpu=gpu)

    def read_region(self, image_path, region=None):
        """
        Read text from image or specific region.

        Args:
            image_path: Path to image
            region: (x, y, width, height) to crop to, or None for full image

        Returns:
            List of (bbox, text, confidence) tuples
        """
        img = cv2.imread(image_path)

        if region:
            x, y, w, h = region
            img = img[y:y+h, x:x+w]

        results = self.reader.readtext(img)
        return results

    def read_scoreboard_regions(self, image_path):
        """Read both scoreboard and formation regions."""
        # Top-left scoreboard (adjust coordinates based on your video resolution)
        scoreboard_results = self.read_region(image_path, region=(0, 0, 400, 100))

        # Bottom-right formation (adjust coordinates)
        formation_results = self.read_region(image_path, region=(800, 600, 1920, 1080))

        return {
            "scoreboard": scoreboard_results,
            "formation": formation_results
        }
```

#### 2.2 Implement Team Matcher (Fixture-Aware)
Create `src/motd_analyzer/ocr/team_matcher.py`:
```python
import json
from difflib import SequenceMatcher

class TeamMatcher:
    def __init__(self, teams_json_path):
        with open(teams_json_path, 'r') as f:
            data = json.load(f)
        self.teams = data['teams']

    def fuzzy_match(self, text, candidate_teams=None, threshold=0.7):
        """
        Match text against known team names (fuzzy matching).

        Args:
            text: OCR text to match
            candidate_teams: Optional list of team names to limit search (from fixtures)
            threshold: Minimum similarity score

        Returns:
            List of (team_name, confidence) tuples
        """
        matches = []
        text_lower = text.lower()

        # If candidate teams provided, only search those (fixture-aware)
        teams_to_search = self.teams
        if candidate_teams:
            teams_to_search = [t for t in self.teams if t['full'] in candidate_teams]

        for team in teams_to_search:
            # Check all name variants
            variants = [team['full'], team['abbrev']] + team['alternates']

            for variant in variants:
                ratio = SequenceMatcher(None, text_lower, variant.lower()).ratio()

                if ratio >= threshold:
                    matches.append((team['full'], ratio))
                    break

        # Return top matches, sorted by confidence
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def extract_teams_from_ocr(self, ocr_results):
        """
        Extract team names from OCR results.

        Args:
            ocr_results: List of (bbox, text, confidence) from EasyOCR

        Returns:
            List of detected teams with confidence scores
        """
        detected_teams = {}

        for (bbox, text, ocr_confidence) in ocr_results:
            matches = self.fuzzy_match(text)

            for team_name, match_confidence in matches:
                # Combined confidence (OCR × fuzzy match)
                combined = ocr_confidence * match_confidence

                # Keep highest confidence for each team
                if team_name not in detected_teams or combined > detected_teams[team_name]:
                    detected_teams[team_name] = combined

        # Return as sorted list
        return sorted(
            [(team, conf) for team, conf in detected_teams.items()],
            key=lambda x: x[1],
            reverse=True
        )
```

#### 2.3 Implement Fixture Matcher
Create `src/motd_analyzer/ocr/fixture_matcher.py`:
```python
import json
from datetime import datetime, timedelta
from difflib import SequenceMatcher

class FixtureMatcher:
    def __init__(self, fixtures_json_path, episode_manifest_path):
        with open(fixtures_json_path, 'r') as f:
            self.fixtures_data = json.load(f)
        with open(episode_manifest_path, 'r') as f:
            self.episodes = json.load(f)['episodes']

    def get_expected_fixtures(self, episode_id):
        """Get expected fixtures for a given episode."""
        episode = next((e for e in self.episodes if e['episode_id'] == episode_id), None)
        if not episode:
            return []

        # Find fixtures by match_id
        expected_matches = []
        for gw in self.fixtures_data['gameweeks']:
            for match in gw['matches']:
                if match['match_id'] in episode['expected_matches']:
                    expected_matches.append(match)

        return expected_matches

    def match_to_fixture(self, ocr_teams, expected_fixtures, threshold=0.7):
        """
        Match OCR-detected teams to expected fixtures.

        Args:
            ocr_teams: List of (team_name, confidence) from OCR
            expected_fixtures: List of fixture dicts
            threshold: Minimum match confidence

        Returns:
            {
                'matched_fixture': fixture dict or None,
                'confidence': float,
                'fixture_validated': bool
            }
        """
        if not ocr_teams or len(ocr_teams) < 2:
            return {'matched_fixture': None, 'confidence': 0.0, 'fixture_validated': False}

        # Get top 2 OCR teams
        team1, conf1 = ocr_teams[0]
        team2, conf2 = ocr_teams[1]

        best_match = None
        best_score = 0.0

        for fixture in expected_fixtures:
            home = fixture['home_team']
            away = fixture['away_team']

            # Check if OCR teams match fixture teams (either order)
            score1 = (SequenceMatcher(None, team1.lower(), home.lower()).ratio() +
                     SequenceMatcher(None, team2.lower(), away.lower()).ratio()) / 2
            score2 = (SequenceMatcher(None, team1.lower(), away.lower()).ratio() +
                     SequenceMatcher(None, team2.lower(), home.lower()).ratio()) / 2

            score = max(score1, score2)

            if score > best_score:
                best_score = score
                best_match = fixture

        if best_score >= threshold:
            return {
                'matched_fixture': best_match,
                'confidence': best_score,
                'fixture_validated': True
            }
        else:
            return {
                'matched_fixture': None,
                'confidence': best_score,
                'fixture_validated': False
            }

    def get_candidate_teams(self, episode_id):
        """Get list of team names to search (from expected fixtures)."""
        fixtures = self.get_expected_fixtures(episode_id)
        teams = set()
        for fixture in fixtures:
            teams.add(fixture['home_team'])
            teams.add(fixture['away_team'])
        return list(teams)
```

#### 2.4 Add OCR Command to CLI (Fixture-Aware)
Update `__main__.py` to add `ocr` command:
```python
def run_ocr(scenes_json_path, teams_json_path, fixtures_path, manifest_path, episode_id, output_path):
    """Run fixture-aware OCR on all scene key frames."""
    with open(scenes_json_path, 'r') as f:
        scenes_data = json.load(f)

    reader = OCRReader(gpu=True)
    matcher = TeamMatcher(teams_json_path)
    fixture_matcher = FixtureMatcher(fixtures_path, manifest_path)

    # Get candidate teams from fixtures (limits search space)
    candidate_teams = fixture_matcher.get_candidate_teams(episode_id)
    expected_fixtures = fixture_matcher.get_expected_fixtures(episode_id)

    results = []
    for scene in scenes_data['scenes']:
        frame_path = scene['key_frame_path']

        # Read OCR
        ocr_results = reader.read_scoreboard_regions(frame_path)

        # Match teams (using candidate teams from fixtures)
        all_ocr = ocr_results['scoreboard'] + ocr_results['formation']
        teams = matcher.extract_teams_from_ocr(all_ocr, candidate_teams=candidate_teams)

        # Match to fixture
        fixture_match = fixture_matcher.match_to_fixture(teams, expected_fixtures)

        results.append({
            "scene_id": scene['scene_id'],
            "frame_path": frame_path,
            "ocr_raw": {
                "scoreboard": [(text, conf) for (_, text, conf) in ocr_results['scoreboard']],
                "formation": [(text, conf) for (_, text, conf) in ocr_results['formation']]
            },
            "detected_teams": teams,
            "fixture_match": fixture_match
        })

    with open(output_path, 'w') as f:
        json.dump({
            "episode_id": episode_id,
            "expected_fixtures": expected_fixtures,
            "ocr_results": results
        }, f, indent=2)

    print(f"OCR complete. Results saved to {output_path}")
    print(f"Searched {len(candidate_teams)} teams (from fixtures) instead of 20")
```

#### 2.5 Run OCR
```bash
python -m motd_analyzer ocr \
  --scenes data/cache/motd_2025_08_17/scenes.json \
  --teams data/teams/premier_league_2025_26.json \
  --fixtures data/fixtures/premier_league_2025_26.json \
  --manifest data/episodes/episode_manifest.json \
  --episode-id motd-2025-08-17 \
  --output data/cache/motd_2025_08_17/ocr_results.json
```

#### 2.6 Manual Validation
1. Open `ocr_results.json`
2. For each scene, check:
   - Did it detect the right teams?
   - Did fixture matching work correctly?
   - Are there false positives?
   - Are there missed teams?
3. Look at frames with low confidence or wrong teams
4. Verify that `fixture_validated: true` appears for match scenes
5. Check if unexpected teams appear (should be flagged)
6. Adjust OCR regions or team matcher threshold if needed

### Validation Checkpoint
- [ ] OCR runs on all frames without errors
- [ ] Team detection accuracy >95% on scenes with visible scoreboards (fixture-aware matching)
- [ ] Fixture matching correctly identifies expected matches
- [ ] No unexpected teams detected (all teams are from expected fixtures)
- [ ] Few false positives (scenes without teams don't incorrectly detect teams)
- [ ] Team name variations are matched correctly (e.g., "Man Utd" → "Manchester United")

### Estimated Time: 6-8 hours

---

## Phase 3: Audio Transcription (Est. 4-6 hours)

### Goals
- Extract audio from video
- Transcribe using Whisper (or faster-whisper)
- Output full transcript with timestamps

### Tasks

#### 3.1 Implement Audio Extractor
Create `src/motd_analyzer/transcription/audio_extractor.py`:
```python
import subprocess
import os

def extract_audio(video_path, output_path):
    """Extract audio track from video as 16kHz mono WAV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # 16-bit PCM
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',  # Mono
        '-y',  # Overwrite
        output_path
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    return output_path
```

#### 3.2 Implement Whisper Transcriber
Create `src/motd_analyzer/transcription/whisper_transcriber.py`:
```python
from faster_whisper import WhisperModel
# OR: import whisper (if using standard whisper)

class WhisperTranscriber:
    def __init__(self, model_size='large-v3', device='auto'):
        # Using faster-whisper
        self.model = WhisperModel(model_size, device=device, compute_type="float16")

        # OR using standard whisper:
        # self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path, language='en'):
        """
        Transcribe audio file.

        Returns:
            Dict with segments and full text
        """
        # faster-whisper API
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True
        )

        results = []
        for segment in segments:
            results.append({
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [
                    {"word": word.word, "start": word.start, "end": word.end}
                    for word in (segment.words or [])
                ]
            })

        return {
            "language": info.language,
            "duration": info.duration,
            "segments": results
        }
```

#### 3.3 Add Transcription Command
Update `__main__.py`:
```python
def run_transcription(video_path, output_path, model_size='large-v3'):
    """Extract audio and transcribe."""
    # Extract audio
    episode_id = os.path.basename(video_path).replace('.mp4', '')
    audio_path = f"data/cache/{episode_id}/audio.wav"

    print(f"Extracting audio from {video_path}...")
    extract_audio(video_path, audio_path)

    # Transcribe
    print(f"Transcribing with Whisper {model_size}... (this will take 10-15 minutes)")
    transcriber = WhisperTranscriber(model_size=model_size)
    transcript = transcriber.transcribe(audio_path)

    # Save
    with open(output_path, 'w') as f:
        json.dump(transcript, f, indent=2)

    print(f"Transcription complete. Saved to {output_path}")
```

#### 3.4 Run Transcription
```bash
# This will take 10-15 minutes for standard whisper, 3-4 mins for faster-whisper
python -m motd_analyzer transcribe \
  --video data/videos/motd_2024_08_17.mp4 \
  --output data/cache/motd_2024_08_17/transcript.json \
  --model large-v3
```

#### 3.5 Manual Validation
1. Open `transcript.json`
2. Spot-check 5-10 segments
3. Listen to corresponding audio sections in the video
4. Check: Is the transcription accurate?
5. Check: Are timestamps roughly correct?

### Validation Checkpoint
- [ ] Audio extraction works
- [ ] Transcription completes without errors
- [ ] Transcription accuracy >95% (spot-check random segments)
- [ ] Timestamps are accurate (±1 second)
- [ ] Word-level timestamps are present

### Estimated Time: 4-6 hours (mostly waiting for transcription)

---

## Phase 4: Analysis & Classification (In Progress - Task 011-012)

**Status:** Task 011 complete (Running Order Detection), Task 012 active (Pipeline Integration + Boundary Detection)

**Completed in Task 011:**
- ✅ Running order detection with 2-strategy approach (scoreboards + FT graphics)
- ✅ 100% consensus on running order (7/7 matches)
- ✅ Pydantic models for type safety (MatchBoundary, RunningOrderResult)
- ✅ 18 passing unit tests with TDD methodology
- ✅ Highlights boundaries detected (first scoreboard → FT graphic)

**Next in Task 012:**
- Wire RunningOrderDetector into pipeline with CLI command
- Implement transcript-based boundary detection for studio intro
- Set match_end = next match's match_start (no gaps)
- Generate JSON output with complete three-segment structure per match

### Goals
- ✅ Detect running order (Task 011 - complete)
- ⏳ Detect match boundaries via transcript (Task 012 - active)
- Calculate airtime per match
- Generate final JSON output

### Current Implementation Status

**Task 011 Deliverables** (Complete ✅):
- `src/motd/pipeline/models.py` - MatchBoundary & RunningOrderResult models
- `src/motd/analysis/running_order_detector.py` - 2-strategy detector with 18 passing tests
- `tests/unit/analysis/test_running_order_detector.py` - Full test coverage

**Task 012 Next Steps** (Active ⏳):
1. Create CLI command: `python -m motd analyze-running-order <episode_id>`
2. Add `detect_match_boundaries()` method to RunningOrderDetector
3. Implement transcript backward search for studio intro detection
4. Set match_end = next match_start (no gaps between matches)
5. Generate JSON output: `data/output/{episode_id}/running_order.json`

**Three Segments Per Match:**
- **Studio Intro:** `match_start` (first team mention in transcript) → `highlights_start` (first scoreboard)
- **Highlights:** `highlights_start` (first scoreboard) → `highlights_end` (FT graphic)
- **Post-Match:** `highlights_end` (FT graphic) → `match_end` (next match_start or episode end)

### Tasks

#### 4.1 Implement Segment Classifier
Create `src/motd_analyzer/analysis/segment_classifier.py`:
```python
class SegmentClassifier:
    """
    Classify scenes into segment types.

    Rules (heuristic-based initially):
    - If OCR detects teams → likely highlights
    - If scene follows highlights and has team names in transcript → analysis
    - If single face detected → interview
    - Default → studio
    """

    def classify_scenes(self, scenes, ocr_results, transcript):
        """
        Classify each scene.

        Returns:
            List of scenes with 'type' and 'confidence' added
        """
        classified = []

        for i, scene in enumerate(scenes):
            scene_id = scene['scene_id']

            # Get OCR for this scene
            ocr = next((r for r in ocr_results if r['scene_id'] == scene_id), None)

            # Get transcript for this time range
            transcript_segment = self._get_transcript_for_time_range(
                transcript, scene['start_time'], scene['end_time']
            )

            # Apply classification rules
            scene_type, confidence = self._classify_single_scene(
                scene, ocr, transcript_segment, i, scenes
            )

            classified.append({
                **scene,
                "type": scene_type,
                "confidence": confidence
            })

        return classified

    def _classify_single_scene(self, scene, ocr, transcript_text, scene_index, all_scenes):
        """Apply heuristic rules to classify a single scene."""

        # Rule 1: If OCR detected 2 teams with high confidence → highlights
        if ocr and len(ocr.get('detected_teams', [])) >= 2:
            if ocr['detected_teams'][0][1] > 0.8:  # confidence > 0.8
                return ("highlights", 0.9)

        # Rule 2: If previous scene was highlights and transcript mentions teams → analysis
        if scene_index > 0:
            prev_scene = all_scenes[scene_index - 1]
            if hasattr(prev_scene, 'type') and prev_scene['type'] == 'highlights':
                if self._contains_team_mention(transcript_text):
                    return ("studio_analysis", 0.75)

        # Rule 3: Check for interview indicators
        # (Would need face detection here - simplified for now)
        if self._is_likely_interview(transcript_text):
            return ("interview", 0.7)

        # Default: studio
        return ("studio", 0.6)

    def _get_transcript_for_time_range(self, transcript, start_time, end_time):
        """Extract transcript text for a time range."""
        # Convert timestamps to seconds
        start_sec = self._timecode_to_seconds(start_time)
        end_sec = self._timecode_to_seconds(end_time)

        text = ""
        for segment in transcript['segments']:
            if start_sec <= segment['start'] <= end_sec:
                text += segment['text'] + " "

        return text.strip()
```

#### 4.2 Implement Team Mention Detector
Create `src/motd_analyzer/analysis/team_mention_detector.py`:
```python
class TeamMentionDetector:
    def __init__(self, teams_json_path):
        with open(teams_json_path, 'r') as f:
            data = json.load(f)
        self.teams = data['teams']

    def find_first_mention(self, transcript_segments):
        """
        Find first team name mentioned in transcript.

        Returns:
            {
                "team": "Arsenal",
                "timestamp": 123.45,
                "text": "So what did you make of Arsenal's performance?"
            }
        """
        for segment in transcript_segments:
            for word in segment.get('words', []):
                word_lower = word['word'].lower()

                # Check against all team name variants
                for team in self.teams:
                    variants = [team['full'], team['abbrev']] + team['alternates']

                    for variant in variants:
                        if variant.lower() in word_lower:
                            return {
                                "team": team['full'],
                                "timestamp": word['start'],
                                "text": segment['text'],
                                "confidence": 0.9
                            }

        return None
```

#### 4.3 Implement Airtime Calculator
Create `src/motd_analyzer/analysis/airtime_calculator.py`:
```python
class AirtimeCalculator:
    def calculate_match_airtime(self, classified_scenes):
        """
        Group scenes by match and calculate total airtime.

        Returns:
            List of matches with segments and total airtime
        """
        matches = []
        current_match = None

        for scene in classified_scenes:
            # Check if this scene has team information (new match detected)
            teams = scene.get('detected_teams', [])

            if len(teams) >= 2 and scene['type'] == 'highlights':
                # Start new match
                if current_match:
                    matches.append(current_match)

                current_match = {
                    "running_order": len(matches) + 1,
                    "teams": [teams[0][0], teams[1][0]],
                    "segments": [],
                    "total_airtime_seconds": 0
                }

            # Add scene to current match
            if current_match:
                current_match['segments'].append({
                    "type": scene['type'],
                    "start": scene['start_time'],
                    "end": scene['end_time'],
                    "duration_seconds": scene['duration_seconds']
                })
                current_match['total_airtime_seconds'] += scene['duration_seconds']

        # Add last match
        if current_match:
            matches.append(current_match)

        return matches
```

#### 4.4 Create Full Pipeline Orchestrator
Create `src/motd_analyzer/pipeline/orchestrator.py`:
```python
class PipelineOrchestrator:
    """Coordinate all pipeline stages."""

    def process(self, video_path, config):
        """Run full pipeline on a video."""
        episode_id = self._get_episode_id(video_path)
        cache_dir = f"data/cache/{episode_id}"

        # Stage 1: Scene Detection
        scenes = self._run_scene_detection(video_path, config, cache_dir)

        # Stage 2: OCR
        ocr_results = self._run_ocr(scenes, config, cache_dir)

        # Stage 3: Transcription
        transcript = self._run_transcription(video_path, config, cache_dir)

        # Stage 4: Analysis
        analysis = self._run_analysis(scenes, ocr_results, transcript, config)

        # Stage 5: Generate final output
        final = self._generate_final_output(episode_id, analysis)

        return final
```

#### 4.5 Run Full Pipeline
```bash
python -m motd_analyzer process data/videos/motd_2024_08_17.mp4 \
  --output data/output/motd_2024_08_17_analysis.json
```

#### 4.6 Manual Validation
1. Open final output JSON
2. Check running order matches video
3. Verify segment classifications (spot-check)
4. Verify first team mentioned in analysis
5. Verify airtime calculations

### Validation Checkpoint
- [ ] Full pipeline runs end-to-end
- [ ] Running order is correct
- [ ] Segment classification >85% accurate
- [ ] Team mentions detected correctly
- [ ] Airtime calculations are accurate

### Estimated Time: 8-10 hours

---

## Phase 5: Manual Validation Tools (Est. 4-6 hours)

### Goals
- Build tools to easily validate and correct results
- Create manual labeling workflow
- Compare automated vs. manual labels

### Tasks

#### 5.1 Create Manual Labeling Tool
Create `src/motd_analyzer/validation/manual_labeler.py`:
```python
"""
Interactive CLI tool to manually label scenes.
"""

def manual_label_scenes(scenes_json_path, output_path):
    """
    Load scenes and prompt user to label each one.
    """
    with open(scenes_json_path, 'r') as f:
        data = json.load(f)

    manual_labels = {}

    for scene in data['scenes']:
        print(f"\n--- Scene {scene['scene_id']} ---")
        print(f"Time: {scene['start_time']} -> {scene['end_time']}")
        print(f"Frame: {scene['key_frame_path']}")

        # Prompt for label
        label = input("Type (studio/highlights/interview/analysis) [skip]: ").strip()

        if label:
            teams = input("Teams (comma-separated) [none]: ").strip()
            notes = input("Notes [none]: ").strip()

            manual_labels[f"scene_{scene['scene_id']}"] = {
                "type": label,
                "teams": teams.split(',') if teams else [],
                "notes": notes,
                "validated_at": datetime.now().isoformat()
            }

    # Save
    with open(output_path, 'w') as f:
        json.dump(manual_labels, f, indent=2)

    print(f"\nManual labels saved to {output_path}")
```

#### 5.2 Create Validation Comparator
Create `src/motd_analyzer/validation/comparator.py`:
```python
def compare_automated_vs_manual(auto_json_path, manual_json_path):
    """
    Compare automated results with manual labels.
    Generate accuracy report.
    """
    with open(auto_json_path, 'r') as f:
        auto = json.load(f)

    with open(manual_json_path, 'r') as f:
        manual = json.load(f)

    report = {
        "total_scenes": len(auto['scenes']),
        "manual_labels": len(manual),
        "accuracy": {
            "segment_classification": {},
            "team_detection": {}
        }
    }

    # Calculate metrics
    correct_classifications = 0
    correct_teams = 0

    for scene in auto['scenes']:
        scene_key = f"scene_{scene['scene_id']}"

        if scene_key in manual:
            # Check classification
            if scene['type'] == manual[scene_key]['type']:
                correct_classifications += 1

            # Check teams
            auto_teams = set(scene.get('detected_teams', []))
            manual_teams = set(manual[scene_key].get('teams', []))

            if auto_teams == manual_teams:
                correct_teams += 1

    report['accuracy']['segment_classification'] = {
        "correct": correct_classifications,
        "total": len(manual),
        "accuracy": correct_classifications / len(manual) if manual else 0
    }

    return report
```

### Validation Checkpoint
- [ ] Manual labeling tool works
- [ ] Can easily review and label scenes
- [ ] Comparison tool generates accurate report

### Estimated Time: 4-6 hours

---

## Phase 6: Refinement & Tuning (Est. 4-8 hours)

### Goals
- Tune thresholds based on validation results
- Fix any major accuracy issues
- Optimise performance if needed
- Prepare for batch processing

### Tasks

#### 6.1 Review Validation Report
- Identify common failure patterns
- Adjust thresholds (scene detection, OCR confidence, etc.)
- Fix classification rules if needed

#### 6.2 Re-run and Re-validate
- Process same video again with tuned parameters
- Compare results
- Iterate until accuracy targets met

#### 6.3 Performance Optimisation (if needed)
- If processing is too slow, consider:
  - Using faster-whisper instead of standard whisper
  - Reducing frame sampling rate for scene detection
  - Using smaller Whisper model (medium instead of large)

### Validation Checkpoint
- [ ] Accuracy >90% on team detection
- [ ] Accuracy >85% on segment classification
- [ ] Processing time acceptable (<2 hours per episode)

### Estimated Time: 4-8 hours

---

## Phase 7: Batch Processing (Est. 2-4 hours)

### Goals
- Process remaining 9 episodes
- Spot-check results
- Generate all output JSON files

### Tasks

#### 7.1 Implement Batch Command
```python
def batch_process(video_dir, output_dir):
    """Process all videos in directory."""
    videos = glob.glob(f"{video_dir}/*.mp4")

    for video in videos:
        print(f"\n{'='*50}")
        print(f"Processing {video}...")
        print(f"{'='*50}\n")

        output_path = f"{output_dir}/{os.path.basename(video).replace('.mp4', '_analysis.json')}"

        orchestrator.process(video, config)
```

#### 7.2 Run Batch Processing
```bash
# Process all episodes (will take 8-12 hours)
python -m motd_analyzer batch data/videos/*.mp4 --output-dir data/output
```

#### 7.3 Spot-Check Results
- Open 2-3 random output files
- Quick manual validation (don't need to check everything)
- Verify no major errors

### Validation Checkpoint
- [ ] All 10 episodes processed successfully
- [ ] No major errors in spot-checked outputs
- [ ] All JSON files are well-formed

### Estimated Time: 2-4 hours (setup) + 8-12 hours (processing)

---

## Phase 8: Documentation & Blog Posts (Est. 4-6 hours)

### Goals
- Document the final pipeline
- Write README with usage instructions
- Prepare blog post content

### Tasks

#### 8.1 Update README
- Installation instructions
- Usage examples
- Configuration guide

#### 8.2 Document Results
- Create summary statistics across all episodes
- Aggregate data for blog analysis

#### 8.3 Prepare Blog Content
- Technical deep-dive: How the pipeline works
- Data analysis: Findings about MOTD coverage bias
- Separate posts for different audiences

### Estimated Time: 4-6 hours

---

## Total Timeline Estimate

| Phase | Description | Time |
|-------|-------------|------|
| 0 | Project Setup | 1-2 hours |
| 1 | Scene Detection | 4-6 hours |
| 2 | OCR & Team Detection | 6-8 hours |
| 3 | Audio Transcription | 4-6 hours |
| 4 | Analysis & Classification | 8-10 hours |
| 5 | Manual Validation Tools | 4-6 hours |
| 6 | Refinement & Tuning | 4-8 hours |
| 7 | Batch Processing | 2-4 hours + 8-12 hours processing |
| 8 | Documentation & Blog | 4-6 hours |
| **Total** | | **37-56 hours (active work) + 8-12 hours (processing)** |

**Realistic Calendar Time**: 2-3 weeks (assuming 2-3 hours per day)

---

## Decision Points

### After Phase 1 (Scene Detection)
**Decision**: Is scene detection accurate enough?
- **If YES**: Proceed to Phase 2
- **If NO**: Tune threshold, consider alternative detector (see tech-tradeoffs.md)

### After Phase 2 (OCR)
**Decision**: Is team detection >90% accurate?
- **If YES**: Proceed to Phase 3
- **If NO**: Consider PaddleOCR, adjust ROI regions, improve team matching logic

### After Phase 3 (Transcription)
**Decision**: Is transcription accurate and fast enough?
- **If YES**: Proceed to Phase 4
- **If NO**: Consider faster-whisper or smaller model

### After Phase 6 (Refinement)
**Decision**: Ready for batch processing?
- **If accuracy targets met**: Proceed to Phase 7
- **If NOT**: Iterate on tuning, consider manual labeling more videos

---

## Risk Mitigation

| Risk | Phase | Mitigation |
|------|-------|------------|
| Scene detection too slow | 1 | Use lower resolution, reduce frame sampling |
| OCR misses teams | 2 | Manual labels for first video, improve ROI |
| Transcription too slow | 3 | Use faster-whisper, smaller model, or cloud API |
| Low classification accuracy | 4 | More manual labels, refine rules, consider ML classifier |
| Processing all videos takes too long | 7 | Run overnight, optimise earlier phases |

---

## Success Metrics (Overall Project)

- [ ] All 10 episodes processed successfully
- [ ] Team detection accuracy >90%
- [ ] Segment classification accuracy >85%
- [ ] Timestamp accuracy >95% (±2 seconds)
- [ ] Processing time <2 hours per episode
- [ ] Clean JSON output ready for blog
- [ ] Reproducible pipeline (can re-run on new episodes)
- [ ] Extensible to podcasts/other leagues

---

## Next Steps After Completion

1. **Blog Posts**: Write up findings and technical approach
2. **MOTD2**: Extend to Sunday night show
3. **Podcasts**: Adapt for audio-only analysis
4. **Dashboard**: Build interactive visualisation
5. **Automation**: Schedule weekly processing of new episodes
6. **Lower Leagues**: Extend to Championship, League One, etc.
