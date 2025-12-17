# MOTD Analyser - Algorithm Overview

> **How MOTD Analyser identifies episode segments and match boundaries**

---

## Workflow

The analyser uses an **LLM-based workflow** for segment detection:

1. **Run automated pipeline** - `python -m motd run <video>` extracts scenes, OCR results, and transcript
2. **Generate LLM prompt** - `python -m motd generate-llm-prompt <episode_id>` creates a prompt with:
   - Deduplicated transcript (Whisper "stutters" removed)
   - Advisory hints from OCR (FT graphics, scoreboard timestamps)
   - Expected fixtures for the broadcast date
   - Segment definitions and output schema
3. **Claude analysis** - Copy prompt to Claude web UI; Claude returns structured JSON
4. **Save results** - Store output at `data/analysis/{episode_id}/analysis.json`

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
