# Technical Architecture

> **Last reviewed:** 2026-01-31

## Design Principles

1. **Modularity**: Each pipeline stage operates independently with clear input/output contracts
2. **Caching**: Intermediate results are cached to avoid expensive re-processing
3. **Reproducibility**: Same input + same config = same output, always
4. **Fail Gracefully**: Pipeline continues if one component fails; errors logged but don't block progress
5. **LLM-Based Analysis**: Final segment detection is performed by Claude using advisory hints from the pipeline

---

## Technology Stack

| Component | Library | Rationale |
|-----------|---------|-----------|
| Scene Detection | PySceneDetect | Purpose-built for scene transitions |
| OCR | EasyOCR | GPU-accelerated, good on sports graphics |
| Transcription | faster-whisper (large-v3) | 4x faster than openai-whisper |
| Fuzzy Matching | rapidfuzz | Team name matching |
| Type Safety | Pydantic v2 | Runtime validation, JSON serialization |
| Video Processing | ffmpeg + opencv-python | Industry standard |

---

## Pipeline Stages

| Stage | Purpose | Output |
|-------|---------|--------|
| 1. Scene Detection | Identify visual transitions | `scenes.json` + `frames/` |
| 2. OCR Processing | Extract team names from FT graphics/scoreboards | `ocr_results.json` |
| 3. Transcription | Convert speech to timestamped text | `transcript.json` |
| 4. LLM Prompt | Combine transcript + OCR hints | `transcript_for_llm.txt` |

All outputs stored in `data/cache/{episode_id}/`.

---

## Configuration

Key settings in `config/config.yaml`:

```yaml
scene_detection:
  threshold: 30.0              # Lower = more sensitive
  min_scene_duration: 3.0

ocr:
  gpu: true
  confidence_threshold: 0.7

transcription:
  model: large-v3
  device: auto                 # auto, cpu, cuda, mps

cache:
  enabled: true
  directory: data/cache
  invalidate_on_config_change: true
```

---

## Caching Strategy

### Cache Structure
```
data/cache/{episode_id}/
├── scenes.json
├── ocr_results.json
├── transcript.json
├── transcript_for_llm.txt
└── frames/
```

### Invalidation Rules

| Change | Invalidates | Re-runs |
|--------|-------------|---------|
| Scene threshold changed | scenes.json | All downstream stages |
| OCR regions changed | ocr_results.json | OCR, analysis |
| Whisper model changed | transcript.json | Transcription, analysis |

---

## Error Handling

### Principles

1. **Fail Gracefully**: One match failing shouldn't block the entire episode
2. **Fail Loudly**: All errors logged with context
3. **Confidence Scores**: Low confidence → flag for review, don't abort

### Error Levels

| Level | Action | Example |
|-------|--------|---------|
| CRITICAL | Abort pipeline | Can't read video, ffmpeg missing |
| ERROR | Skip item, continue | OCR fails on one scene |
| WARNING | Flag for review | Low confidence detection |

### Confidence Thresholds

- **>0.9**: Auto-accept
- **0.7-0.9**: Accept, log for spot-check
- **<0.7**: Flag for manual review

---

## Performance

### Processing Times (M3 Pro, 90-min episode)

| Stage | Duration | Bottleneck |
|-------|----------|------------|
| Scene Detection | 5-8 min | CPU-bound |
| OCR Processing | 8-12 min | GPU-bound |
| Transcription | 15-20 min | CPU-bound (no MPS support) |
| LLM Prompt | <30 sec | CPU-bound |
| **Total (first run)** | **30-35 min** | |
| **Cached run** | **<1 min** | |

### Resource Usage

- **RAM**: ~12-16GB peak
- **Disk**: ~800MB-1GB per episode (cache + frames)

**Note**: faster-whisper runs on CPU on Apple Silicon because CTranslate2 doesn't support MPS yet.
