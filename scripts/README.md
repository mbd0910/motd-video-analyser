# Debugging Scripts

This directory contains debugging tools for manual verification and calibration when working on the MOTD Analyser project.

## Available Scripts

### `debug_fixtures.py`

Debug fixture matcher for a given episode. Useful for verifying fixture data when adding new episodes.

```bash
# List all episodes in manifest
python scripts/debug_fixtures.py --list

# Show fixtures for specific episode
python scripts/debug_fixtures.py motd_2025-26_2025-11-01

# Validate detected teams against episode
python scripts/debug_fixtures.py motd_2025-26_2025-11-01 --validate "Liverpool,Arsenal"
```

### `debug_ocr_region.py`

Debug OCR region extraction on a single frame. Useful when calibrating OCR regions (e.g., after BBC changes video resolution).

```bash
# Extract all regions from a frame
python scripts/debug_ocr_region.py data/cache/motd_2025-26_2025-11-01/frames/frame_0001.jpg

# Extract specific region
python scripts/debug_ocr_region.py frame.jpg --region ft_score

# Save extracted regions to files
python scripts/debug_ocr_region.py frame.jpg --save

# Run EasyOCR on extracted regions
python scripts/debug_ocr_region.py frame.jpg --ocr
```

### `visualize_regions.py`

Visualise OCR regions overlaid on video frames. Draws coloured boxes showing where each OCR region is configured.

```bash
# Annotate a single frame
python scripts/visualize_regions.py frame.jpg

# Save to specific path
python scripts/visualize_regions.py frame.jpg --output /tmp/annotated.jpg

# Batch process all frames for an episode
python scripts/visualize_regions.py --episode motd_2025-26_2025-11-01

# Process first 10 frames only
python scripts/visualize_regions.py --episode motd_2025-26_2025-11-01 --limit 10
```

## When to Use These Scripts

| Scenario | Script |
|----------|--------|
| Adding new episode to manifest | `debug_fixtures.py` |
| BBC changes video resolution | `debug_ocr_region.py`, `visualize_regions.py` |
| OCR not detecting expected text | `debug_ocr_region.py --ocr` |
| Verifying OCR region calibration | `visualize_regions.py` |
| Debugging fixture matching failures | `debug_fixtures.py --validate` |

## Configuration

All scripts read OCR regions from `config/config.yaml`. If you need to adjust regions, edit the config file and re-run the scripts to verify.

```yaml
# config/config.yaml
ocr:
  regions:
    ft_score:       # Full-time score graphic (primary)
      x: 157
      y: 545
      width: 966
      height: 140
    scoreboard:     # Live scoreboard (secondary)
      x: 0
      y: 0
      width: 370
      height: 70
    formation:      # Formation graphic (validation)
      x: 533
      y: 400
      width: 747
      height: 320
```
