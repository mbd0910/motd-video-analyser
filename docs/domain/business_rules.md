# Business Rules

> **Last reviewed:** 2025-12-18

**Purpose:** Document the validation rules enforced by the automated pipeline that produce advisory hints for LLM analysis. The pipeline extracts scenes, OCR results, and transcripts; Claude (LLM) performs the actual segment analysis using these hints.

**Workflow context:** See [algorithm.md](../algorithm.md) for the full LLM-based workflow.

---

## Table of Contents

1. [Rule 1: FT Graphic Validation](#rule-1-ft-graphic-validation)
2. [Rule 2: Episode Manifest Constraint](#rule-2-episode-manifest-constraint)
3. [Rule 3: Opponent Inference from Fixtures](#rule-3-opponent-inference-from-fixtures)
4. [LLM Analysis Context](#llm-analysis-context)

---

## Rule 1: FT Graphic Validation

### Source Code
**File:** `src/motd/ocr/validators.py:103-160`
**Method:** `GraphicValidator.validate_ft_graphic()`

### Definition

A frame contains a valid FT (full-time) graphic if it passes either tier:

**Tier 1 (Strong):** ≥1 team detected + FT indicator present
**Tier 2 (Fallback):** Score pattern + FT indicator (when team names missed by OCR)

**FT indicators:** `FT`, `FULL TIME`, `FULL-TIME`, `FULLTIME`
**Score pattern:** `\b\d+\s*[-–—|]?\s*\d+\b` (handles BBC pipe `|` and OCR variants)

### What This Filters Out

- **Possession bars** - Numbers but no "FT" text
- **Player statistics** - Names/numbers but no FT
- **Formation graphics** - Team names but no FT
- **Half-time scores** - "HT" instead of "FT"

### Output

Validated FT graphics are included in `ocr_results.json` as advisory hints for the LLM to identify match boundaries.

---

## Rule 2: Episode Manifest Constraint

### Source Code
**File:** `src/motd/ocr/fixture_matcher.py:98-167`
**Methods:** `get_expected_fixtures()`, `get_expected_teams()`

### Definition

The episode manifest (`data/episodes/episode_manifest.json`) defines which fixtures are expected in each episode. OCR team matching uses this to **reduce search space** from 20 Premier League teams to the ~14 teams expected in that episode's fixtures.

**Episode manifest structure:**
```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "expected_matches": [
    "2025-11-01-liverpool-astonvilla",
    "2025-11-01-burnley-arsenal"
  ]
}
```

### Purpose

1. **Search space reduction:** Fuzzy matching against 14 expected teams vs all 20
2. **Disambiguation:** "LIVRPOOL" → Liverpool (only if Liverpool in expected teams)
3. **Warning generation:** Unexpected teams flagged in logs for review

### What This Does NOT Do

- Does NOT block unexpected teams (warnings only)
- Does NOT apply confidence boosts

---

## Rule 3: Opponent Inference from Fixtures

### Source Code
**File:** `src/motd/ocr/scene_processor.py:255-314`
**Method:** `SceneProcessor._infer_opponent()`

### Definition

When OCR detects **exactly 1 team** in an FT graphic (FT validation passes), the opponent is inferred from the episode's fixture list.

**Trigger conditions:**
1. FT validation passes (Rule 1) ✓
2. Exactly 1 team detected via OCR
3. Detected team in episode's expected fixtures

**Process:**
1. Find fixture containing detected team
2. Extract opponent (the other team)
3. Add opponent with confidence 0.75, source: `inferred_from_fixture`

### Why This Exists

BBC FT graphics use bold text for home team (95%+ OCR accuracy) and regular text for away team (60-70% OCR accuracy). Opponent inference recovers ~70% of single-team detections.

**Example:**
- OCR reads: "Liverpool 2 0 FT" (misses "Aston Villa")
- Fixtures: liverpool-astonvilla
- Result: Infers "Aston Villa" as opponent (confidence 0.75)

### Confidence Levels

| Source | Confidence | Notes |
|--------|-----------|-------|
| OCR-detected team | 0.85-0.95 | Directly read from frame |
| Inferred opponent | 0.75 | Derived from fixtures, not observed |

---

## LLM Analysis Context

The rules above produce **advisory hints** that are included in the LLM prompt. The actual analysis decisions are made by Claude:

### What the Pipeline Produces (Automated)

1. **scenes.json** - Scene boundaries with timestamps
2. **ocr_results.json** - FT graphics and scoreboard detections (with validation)
3. **transcript.json** - Full episode transcript with word-level timestamps

### What Claude Determines (LLM Analysis)

1. **Running order** - Which matches appear and in what sequence
2. **Segment boundaries** - Where each segment starts/ends
3. **Segment classification** - Type of each segment (studio intro, highlights, etc.)

### Output

Claude's analysis is saved to `data/analysis/{episode_id}/analysis.json`. See [analysis_schema.md](analysis_schema.md) for the expected output format.

---

## Related Documentation

- [Algorithm Overview](../algorithm.md) - Full LLM-based workflow
- [Domain Glossary](README.md#glossary) - Terminology definitions
- [Visual Patterns](visual_patterns.md) - MOTD episode structure
- [Analysis Schema](analysis_schema.md) - LLM output format
