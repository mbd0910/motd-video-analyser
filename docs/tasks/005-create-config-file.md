# Task 005: Create Configuration File

## Objective
Create the main config.yaml file with all pipeline parameters.

## Prerequisites
- [004-create-team-names-file.md](004-create-team-names-file.md) completed

## Steps

### 1. Create config.yaml
```bash
cat > config/config.yaml << 'EOF'
# Scene Detection Configuration
scene_detection:
  threshold: 30.0              # Scene detection sensitivity (lower = more sensitive)
  min_scene_duration: 3.0      # Minimum scene length in seconds

# OCR Configuration
ocr:
  library: easyocr             # OCR library to use
  languages: ['en']            # Languages for OCR
  gpu: true                    # Use GPU acceleration if available
  confidence_threshold: 0.7    # Minimum confidence for automatic acceptance

  # Regions of interest (ROI) for OCR - adjust based on video resolution
  # These coordinates are for 1920x1080 video
  regions:
    scoreboard:                # Top-left scoreboard graphic
      x: 0
      y: 0
      width: 400
      height: 100
    formation:                 # Bottom-right formation graphic
      x: 800
      y: 600
      width: 1920
      height: 1080

# Transcription Configuration
transcription:
  model: large-v3              # Whisper model size (tiny, base, small, medium, large, large-v3)
  language: en                 # Language code
  device: auto                 # Device: auto, cpu, cuda, mps (auto will use GPU if available)
  word_timestamps: true        # Enable word-level timestamps

# Team Names
teams:
  path: data/teams/premier_league_2025_26.json

# Caching Configuration
cache:
  enabled: true
  directory: data/cache
  invalidate_on_config_change: true  # Re-run if config changes

# Output Configuration
output:
  directory: data/output
  format: json
  indent: 2                    # JSON indentation for readability
  include_metadata: true       # Include processing metadata in output

# Logging Configuration
logging:
  level: INFO                  # DEBUG, INFO, WARNING, ERROR
  file: logs/pipeline.log
  console: true                # Also log to console
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
EOF
```

### 2. Validate YAML
```bash
python -c "import yaml; config = yaml.safe_load(open('config/config.yaml')); print('Config valid. Keys:', list(config.keys()))"
```

Should output: `Config valid. Keys: ['scene_detection', 'ocr', 'transcription', 'teams', 'cache', 'output', 'logging']`

## Validation Checklist
- [ ] File created at `config/config.yaml`
- [ ] YAML is valid (Python can parse it)
- [ ] All required sections present

## Estimated Time
5 minutes

## Notes

### Configuration Tuning
You'll likely need to adjust these parameters after testing:

- **scene_detection.threshold**: If too many/few scenes detected, adjust this
  - Lower = more sensitive (more scenes)
  - Higher = less sensitive (fewer scenes)
  - Typical range: 20-40

- **ocr.regions**: Adjust based on your video resolution
  - Run `ffprobe` on your video to check resolution
  - BBC iPlayer videos are typically 1920x1080 or 1280x720

- **transcription.model**: Trade-off between speed and accuracy
  - `large-v3`: Best accuracy, slowest (~10-15 mins for 90-min video)
  - `medium`: Good accuracy, faster (~5-7 mins)
  - `small`: Decent accuracy, fast (~3-5 mins)

## Next Task
Phase 0 complete! Move to Phase 1:
[006-implement-scene-detector.md](006-implement-scene-detector.md)
