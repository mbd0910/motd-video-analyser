# MOTD Analyser - Algorithm Overview

> **Last reviewed:** 2025-12-18

> **How MOTD Analyser identifies episode segments and match boundaries**

---

## Workflow

The analyser uses an **LLM-based workflow** for segment detection:

1. **Run automated pipeline** - `python -m motd run <video>` executes all 4 stages:
   - Stage 1: Scene Detection (video → scenes.json + frames/)
   - Stage 2: Team Extraction via OCR (→ ocr_results.json)
   - Stage 3: Transcription via Whisper (→ transcript.json)
   - Stage 4: LLM Prompt Generation (→ transcript_for_llm.txt)

2. **Claude analysis** - Copy the generated prompt to Claude web UI; Claude returns structured JSON
   - The prompt includes: deduplicated transcript, OCR advisory hints, expected fixtures, and output schema

3. **Save results** - Store Claude's output at `data/analysis/{episode_id}/analysis.json`

**Standalone commands** are also available for individual stages:
- `python -m motd detect-scenes <video>` - Scene detection only
- `python -m motd extract-teams --scenes <scenes.json> --episode-id <id>` - OCR only
- `python -m motd transcribe <video>` - Transcription only
- `python -m motd generate-llm-prompt <episode_id>` - Prompt generation only

The LLM-based approach replaced an earlier rule-based strategy, which struggled with nuanced segment boundaries.

---

## Advisory Hints

The automated pipeline stages produce hints that improve LLM accuracy:

| Stage | Output | How It Helps |
|-------|--------|--------------|
| Scene Detection | Extracted frames (~2,600 per episode) | Visual reference (not currently in prompt) |
| OCR | FT graphics + scoreboard timestamps | Anchor segment boundaries |
| Transcription | Word-level transcript | Primary input for LLM analysis |
| Fixtures | Expected matches for broadcast date | Validates team detections |

### FT Graphics (Full-Time Graphics)

The OCR stage prioritises **FT graphics** - the full-time score display at the end of each match's highlights:

- **Lower-middle region** of frame (720p coordinates)
- Validation: ≥1 team detected + score pattern + "FT" text
- 90-95% accuracy (static, bold text)

### Scoreboards (Backup)

Live scoreboards during highlights provide backup hints:

- **Top-left region** of frame
- 75-85% accuracy (motion blur from camera panning)
- Used when FT graphics are missed

### Opponent Inference

When OCR detects only one team in an FT graphic:

1. Check episode manifest for that team's fixture
2. Infer opponent from home/away pairing
3. Mark as `inferred_from_fixture` with lower confidence (0.75)

---

## Episode Structure

Match of the Day episodes follow a predictable pattern:

```
Episode Start
    ↓
Studio Intro (Match 1)
    ↓
Team Lineups
    ↓
Match Highlights (scoreboard visible)
    ↓
FT Graphic (full-time score)
    ↓
Post-Match Analysis
    ↓
[Repeat for each match...]
    ↓
League Table Review
    ↓
Episode End
```

The LLM identifies these segments from the transcript, using OCR hints to anchor timestamps.

---

## Output Schema

The LLM returns structured JSON with:

**Episode-level segments:**
- `intro` - Opening with pundit introductions
- `league_table` - League standings review (if present)
- `next_motd_promo` - Promo for next episode (if present)
- `outro` - Closing credits

**Per-match segments:**
- `studio_intro` - Pundit discussion before highlights
- `lineups` - Formation graphics and team walkthrough
- `highlights` - Match footage with commentary
- `post_match_interviews` - Pitchside interviews
- `studio_analysis` - Post-match pundit discussion

See [analysis_schema.md](domain/analysis_schema.md) for the complete JSON schema.

---

## Technical Details

For implementation specifics, see:
- **[architecture.md](architecture.md)** - Pipeline stages (scene detection, OCR, transcription)
- **[Domain Glossary](domain/README.md)** - Terminology (FT graphics, running order, etc.)
- **[Business Rules](domain/business_rules.md)** - Validation rules for OCR hints
- **[Visual Patterns](domain/visual_patterns.md)** - Episode structure, timing patterns

---

**Up the Addicks!** ⚽🔴⚪
