# Technology & Library Trade-offs

This document provides detailed analysis of library choices for the MOTD Analyser, including alternatives and migration paths. Use this as a reference if you need to pivot from the chosen technologies.

---

## Scene Detection

### Current Choice: PySceneDetect

**Why**:
- Purpose-built for scene transition detection
- Handles complex transitions (fades, dissolves, cuts)
- Multiple detection algorithms (ContentDetector, ThresholdDetector, AdaptiveDetector)
- Well-maintained, active community
- Simple API: `detect_scenes(video_path, detector)`

**Trade-offs**:
- Slightly slower than raw OpenCV (but more accurate)
- Additional dependency (vs. just using OpenCV directly)

**Installation**:
```bash
pip install scenedetect[opencv]
```

**Usage Example**:
```python
from scenedetect import detect, ContentDetector

scenes = detect('video.mp4', ContentDetector(threshold=30))
for scene in scenes:
    print(f"Scene: {scene[0].get_timecode()} -> {scene[1].get_timecode()}")
```

---

### Alternative 1: Raw OpenCV (Frame Difference)

**When to use**: If PySceneDetect is too slow or you need fine-grained control

**Pros**:
- Full control over algorithm
- No additional dependencies
- Potentially faster (optimised for your use case)

**Cons**:
- More code to write and maintain
- Misses subtle transitions (fades, dissolves)
- Need to tune threshold manually

**Migration Effort**: Low (1-2 hours)

**Example**:
```python
import cv2
import numpy as np

def detect_scenes_opencv(video_path, threshold=30):
    cap = cv2.VideoCapture(video_path)
    prev_frame = None
    scenes = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            mean_diff = np.mean(diff)

            if mean_diff > threshold:
                scenes.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)

        prev_frame = gray

    return scenes
```

**Benchmark** (90-min video):
- PySceneDetect: ~5 minutes
- Raw OpenCV: ~3 minutes (but may miss transitions)

---

### Alternative 2: TransNetV2 (ML-Based)

**When to use**: If accuracy is critical and you need to detect very subtle transitions

**Pros**:
- State-of-the-art accuracy (trained on large dataset)
- Detects gradual transitions (fades, dissolves) extremely well
- Pre-trained model available

**Cons**:
- Requires TensorFlow (heavy dependency)
- Slower than PySceneDetect (~2-3x)
- Overkill for MOTD (BBC uses simple cuts mostly)

**Migration Effort**: Medium (3-4 hours)

**Installation**:
```bash
pip install transnetv2
```

**Recommendation**: **Stick with PySceneDetect** unless you're getting many missed transitions.

---

## OCR (Optical Character Recognition)

### Current Choice: EasyOCR

**Why**:
- Excellent accuracy on stylized text (sports graphics, logos)
- GPU acceleration (leverages M3 Pro)
- Simple API: `reader.readtext(image)`
- Supports 80+ languages (future-proof)
- Active development

**Trade-offs**:
- Slower than PaddleOCR (~2x)
- Model download on first run (~100MB)

**Installation**:
```bash
pip install easyocr
```

**Usage Example**:
```python
import easyocr

reader = easyocr.Reader(['en'], gpu=True)
results = reader.readtext('frame.jpg')

for (bbox, text, confidence) in results:
    print(f"Text: {text}, Confidence: {confidence:.2f}")
```

**Benchmark** (per frame):
- ~200-300ms per frame on M3 Pro (GPU)
- ~500-800ms per frame on CPU

---

### Alternative 1: PaddleOCR

**When to use**: If processing speed becomes critical

**Pros**:
- **Fastest** OCR library (C++ backend)
- High accuracy (comparable to EasyOCR)
- Lower memory usage
- GPU acceleration

**Cons**:
- Slightly more complex setup
- Less accurate on very stylized fonts
- Documentation primarily in Chinese (though English exists)

**Migration Effort**: Low (2-3 hours)

**Installation**:
```bash
pip install paddlepaddle paddleocr
```

**Usage Example**:
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)
results = ocr.ocr('frame.jpg', cls=True)

for line in results[0]:
    text = line[1][0]
    confidence = line[1][1]
    print(f"Text: {text}, Confidence: {confidence:.2f}")
```

**Benchmark** (per frame):
- ~100-150ms per frame on M3 Pro (GPU)
- ~300-500ms per frame on CPU

**When to switch**: If you're processing >100 frames and speed matters

---

### Alternative 2: Tesseract

**When to use**: Never for this use case (included for completeness)

**Pros**:
- Most mature OCR library
- Very accurate on plain text (documents, books)
- Lightweight

**Cons**:
- **Poor accuracy on sports graphics** (stylised fonts, coloured backgrounds)
- No GPU acceleration
- Requires system-level installation (not just pip)

**Migration Effort**: Low (1-2 hours), but **not recommended**

**Benchmark** (per frame):
- ~500-1000ms per frame
- Accuracy on MOTD graphics: ~60-70% (vs. 90%+ for EasyOCR/PaddleOCR)

**Recommendation**: **Avoid Tesseract for this project**

---

### Comparison Table: OCR Libraries

| Library | Accuracy (MOTD) | Speed (M3 Pro GPU) | Ease of Use | Recommendation |
|---------|-----------------|---------------------|-------------|----------------|
| **EasyOCR** | ★★★★★ (95%+) | ★★★☆☆ (200-300ms) | ★★★★★ | **Current Choice** |
| **PaddleOCR** | ★★★★☆ (90%+) | ★★★★★ (100-150ms) | ★★★☆☆ | Switch if speed critical |
| **Tesseract** | ★★☆☆☆ (60-70%) | ★★☆☆☆ (500-1000ms) | ★★★☆☆ | Avoid |

---

## Speech-to-Text (Transcription)

### Current Choice: OpenAI Whisper (Local, large-v3)

**Why**:
- **Best-in-class accuracy** (state-of-the-art)
- Handles multiple speakers, accents, background noise
- Free (runs locally)
- Word-level timestamps (critical for team mention detection)
- Your M3 Pro has plenty of RAM (36GB) for large model

**Trade-offs**:
- Slower than cloud APIs (~10-15 mins for 90-min video)
- GPU memory intensive (large model needs ~10GB VRAM)

**Installation**:
```bash
pip install openai-whisper
```

**Usage Example**:
```python
import whisper

model = whisper.load_model("large-v3")
result = model.transcribe("audio.wav", language="en", word_timestamps=True)

for segment in result['segments']:
    print(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s] {segment['text']}")
```

**Benchmark** (90-min video, M3 Pro):
- **large-v3**: ~12-15 minutes
- **medium**: ~6-8 minutes
- **small**: ~3-5 minutes

---

### Alternative 1: OpenAI Whisper API (Cloud)

**When to use**: If processing speed is critical and you're willing to pay

**Pros**:
- **Much faster** (~2-3 mins for 90-min video)
- No local compute needed
- Same accuracy as local large model

**Cons**:
- **Costs money** (~$0.006/minute → ~$0.54 per episode → ~$5.40 for 10 episodes)
- Requires internet connection
- Data leaves your machine (BBC might not like this)

**Migration Effort**: Very low (<1 hour)

**Installation**:
```bash
pip install openai
```

**Usage Example**:
```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

with open("audio.wav", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )

print(transcript.text)
```

**Cost Breakdown**:
- 10 episodes × 90 mins = 900 minutes
- 900 × $0.006 = **$5.40 total**

**When to switch**: If 15 mins/episode is too slow, $5.40 is acceptable cost

---

### Alternative 2: Faster-Whisper

**When to use**: If you want local processing but faster than vanilla Whisper

**Pros**:
- **4-5x faster** than standard Whisper (CTranslate2 backend)
- Same accuracy
- Lower memory usage
- Still free and local

**Cons**:
- Additional dependency
- Slightly more complex setup

**Migration Effort**: Very low (1 hour)

**Installation**:
```bash
pip install faster-whisper
```

**Usage Example**:
```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="auto", compute_type="float16")
segments, info = model.transcribe("audio.wav", language="en", word_timestamps=True)

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

**Benchmark** (90-min video, M3 Pro):
- **large-v3**: ~3-4 minutes (vs. 12-15 mins for standard Whisper)
- **medium**: ~2-3 minutes
- **small**: ~1-2 minutes

**Recommendation**: **Strongly consider switching to faster-whisper** - same accuracy, 4x faster, still local and free.

---

### Comparison Table: Transcription Options

| Option | Accuracy | Speed (90min) | Cost | Local/Cloud | Recommendation |
|--------|----------|---------------|------|-------------|----------------|
| **Whisper (local)** | ★★★★★ | 12-15 mins | Free | Local | Current choice |
| **faster-whisper** | ★★★★★ | 3-4 mins | Free | Local | **Upgrade to this** |
| **Whisper API** | ★★★★★ | 2-3 mins | $0.54/ep | Cloud | If speed > cost |
| **AssemblyAI** | ★★★★☆ | 3-5 mins | $0.75/ep | Cloud | Alternative cloud |
| **Google Speech** | ★★★☆☆ | 2-4 mins | $0.024/min | Cloud | Avoid (lower accuracy) |

---

## Video Processing

### Current Choice: ffmpeg + opencv-python

**Why**:
- **Industry standard** for video manipulation
- Extremely fast and reliable
- opencv-python for Python bindings
- All features needed (extract audio, frames, metadata)

**Trade-offs**:
- System dependency (ffmpeg must be installed separately)
- Command-line tool (called via subprocess)

**Installation**:
```bash
# macOS
brew install ffmpeg

# Python bindings
pip install opencv-python
```

**Usage Example**:
```python
import subprocess

# Extract audio
subprocess.run([
    'ffmpeg', '-i', 'video.mp4',
    '-vn', '-acodec', 'pcm_s16le',
    '-ar', '16000', 'audio.wav'
])

# Extract frame at timestamp
subprocess.run([
    'ffmpeg', '-i', 'video.mp4',
    '-ss', '00:01:30', '-frames:v', '1',
    'frame.jpg'
])
```

---

### Alternative: moviepy

**When to use**: If you want pure-Python solution (no system dependencies)

**Pros**:
- Pure Python (no ffmpeg required)
- Simpler API for basic operations
- Good for programmatic video editing

**Cons**:
- Slower than ffmpeg
- Less mature, fewer features
- Higher memory usage

**Migration Effort**: Low (2-3 hours)

**Installation**:
```bash
pip install moviepy
```

**Usage Example**:
```python
from moviepy.editor import VideoFileClip

clip = VideoFileClip("video.mp4")

# Extract audio
clip.audio.write_audiofile("audio.wav")

# Extract frame at timestamp
clip.save_frame("frame.jpg", t=90)  # at 90 seconds
```

**Recommendation**: **Stick with ffmpeg** - faster, more reliable, industry standard

---

## Configuration Management

### Current Choice: PyYAML

**Why**:
- Human-readable config files
- Standard in Python ecosystem
- Simple API
- Supports comments (unlike JSON)

**Installation**:
```bash
pip install pyyaml
```

**Usage Example**:
```python
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

threshold = config['scene_detection']['threshold']
```

---

### Alternative: TOML (tomli/tomllib)

**When to use**: If you prefer TOML syntax (more structured than YAML)

**Pros**:
- More explicit than YAML (less ambiguity)
- Built into Python 3.11+ (tomllib)
- Growing popularity (pyproject.toml standard)

**Cons**:
- Less widely used for config files
- Slightly more verbose

**Migration Effort**: Very low (<1 hour)

**Recommendation**: **Stick with YAML** unless you have strong TOML preference

---

## CLI Framework

### Current Choice: argparse

**Why**:
- Built into Python (no dependency)
- Simple for basic CLI needs
- Good enough for this project

**Usage Example**:
```python
import argparse

parser = argparse.ArgumentParser(description='MOTD Analyser')
parser.add_argument('video', help='Path to video file')
parser.add_argument('--output', help='Output JSON path')
args = parser.parse_args()
```

---

### Alternative: Click

**When to use**: If CLI becomes complex (many subcommands, options)

**Pros**:
- Cleaner API for complex CLIs
- Better help messages
- Command groups, aliases, etc.

**Cons**:
- Additional dependency

**Migration Effort**: Low (1-2 hours)

**Installation**:
```bash
pip install click
```

**Usage Example**:
```python
import click

@click.command()
@click.argument('video')
@click.option('--output', help='Output JSON path')
def process(video, output):
    click.echo(f'Processing {video}...')
```

**Recommendation**: Start with **argparse**, migrate to Click if CLI grows complex

---

## Summary & Decision Matrix

### When to Switch Technologies

| Current | Switch To | When | Effort |
|---------|-----------|------|--------|
| PySceneDetect | Raw OpenCV | Need more speed, willing to sacrifice subtle transition detection | Low |
| EasyOCR | PaddleOCR | Speed critical, processing >100 frames | Low |
| EasyOCR | Tesseract | **Never** (poor accuracy on sports graphics) | N/A |
| Whisper (local) | faster-whisper | Want 4x speed, keep local/free | Low |
| Whisper (local) | Whisper API | Speed critical, $5-10 cost acceptable | Very Low |
| ffmpeg | moviepy | Want pure Python, no system deps | Low |
| YAML | TOML | Personal preference | Very Low |
| argparse | Click | CLI becomes complex (>5 subcommands) | Low |

---

## Recommended Immediate Upgrade

**Switch from `openai-whisper` to `faster-whisper`**:
- Same accuracy
- 4x faster (3-4 mins vs. 12-15 mins per episode)
- Still local and free
- Minimal code change

**Why**: No downside, significant performance gain. This is a no-brainer upgrade.

---

## Future Considerations

### For Podcast Extension
- Keep: faster-whisper, team matching logic
- Add: **pyannote.audio** for speaker diarization (identify who's speaking)

### For Real-Time Processing
- Switch: Whisper API (faster) or AssemblyAI (real-time streaming)
- Add: Redis for job queue, Celery for background processing

### For Web Dashboard
- Add: **FastAPI** for REST API layer
- Add: **SQLite** or **PostgreSQL** for result storage
- Frontend: **React** or **Next.js** consuming JSON API
