# Domain Documentation

**Purpose:** This directory contains the single source of truth for MOTD Analyser's business domain knowledge, terminology, and rules. All sub-tasks should reference these documents rather than duplicating context.

---

## Table of Contents

1. [Glossary](#glossary) - Core terminology and definitions
2. [Data Relationships](#data-relationships) - How episodes, fixtures, and teams relate
3. [Key Workflows](#key-workflows) - Common business processes

**Related Documentation:**
- [Business Rules](business_rules.md) - Detailed validation and processing rules
- [Visual Patterns](visual_patterns.md) - MOTD episode structure and visual elements

---

## Glossary

### Visual Elements

#### FT Graphic
**Definition:** Full-time score graphic displayed at the end of match highlights, showing final score with both team names.

**Characteristics:**
- Static image (no motion blur)
- Clean, readable text
- Both teams visible (home and away)
- Final score prominently displayed (e.g., "2-1", "3 | 0")
- "FT" or "FULL TIME" label present
- Appears for 2-4 seconds at match conclusion

**Example:**
```
┌─────────────────────────────┐
│  Liverpool    2              │
│  Aston Villa  0    FT        │
└─────────────────────────────┘
```

**Why It Matters:** FT graphics are the gold standard for team detection via OCR. They provide:
- Highest accuracy (clean, static text)
- Both teams in single frame
- Score validation (confirms match pairing)
- Definitive match boundary marker

**Typical Duration:** Visible for 2-4 seconds, but may be as brief as 10 frames (0.3s) in fast-paced edits.

#### Scoreboard
**Definition:** Live score overlay in the top-left corner during match highlights, continuously visible throughout footage.

**Characteristics:**
- Always present during match footage
- Small text (harder for OCR)
- Often motion-blurred (camera panning)
- May be partially obscured (e.g., by pitch markings)
- Updates throughout match (not just final score)

**Example:**
```
┌──────────────┐
│ LIV 2-0 AVL  │ ← Top-left corner
└──────────────┘
```

**Why It Matters:** Scoreboards are a fallback when FT graphics aren't detected. Less accurate than FT graphics but more consistently present.

**OCR Challenge:** Motion blur from camera movement makes text recognition unreliable (60-70% accuracy vs 95%+ for FT graphics).

#### Formation Graphic
**Definition:** Team lineup display shown at the start of match highlights, displaying starting XI in tactical formation.

**Characteristics:**
- Static image (clean text)
- Team names visible at top
- Player names in formation layout
- NO score information
- Appears for 3-5 seconds at match start

**Example:**
```
┌─────────────────────────────┐
│     Liverpool                │
│                              │
│      Salah                   │
│  Robertson  Van Dijk  Arnold │
│         Fabinho              │
└─────────────────────────────┘
```

**Why It Matters:** Useful for team detection when FT graphics aren't available, but lacks score validation.

**Limitation:** Cannot determine match outcome or confirm team pairing (both teams rarely shown in single frame).

---

### Data Concepts

#### Episode
**Definition:** A single Match of the Day broadcast episode, identified by season and broadcast date.

**Format:** `motd_YYYY-YY_YYYY-MM-DD`

**Example:** `motd_2025-26_2025-11-01` (2025/26 season, broadcast on 1 November 2025)

**Key Properties:**
- Broadcast date (Saturday evening, typically 22:30 GMT)
- Duration (60-90 minutes depending on number of matches)
- Expected matches (7-8 fixtures from that gameweek)
- Running order (editorial sequence, not chronological)

**Data File:** `data/episodes/episode_manifest.json`

#### Episode Manifest
**Definition:** JSON file mapping each episode to its expected fixtures and metadata.

**Purpose:** Defines which matches appear in each episode, enabling fixture-aware OCR validation.

**Why It Exists:**
- MOTD does NOT show all matches from a gameweek
- Some matches are exclusive to Sky Sports, TNT Sports, or Amazon Prime
- Typically shows 7 matches out of 10 played on Saturday
- BBC selects fixtures based on broadcast rights and editorial interest

**Example Structure:**
```json
{
  "episode_id": "motd_2025-26_2025-11-01",
  "broadcast_date": "2025-11-01",
  "season": "2025-26",
  "expected_matches": [
    "2025-11-01-liverpool-astonvilla",
    "2025-11-01-burnley-arsenal",
    "2025-11-01-chelsea-newcastle",
    "2025-11-01-manchester_city-southampton",
    "2025-11-01-west_ham-brighton",
    "2025-11-01-wolves-nottingham_forest",
    "2025-11-01-fulham-brentford"
  ]
}
```

**How It's Created:** Manually, by reviewing BBC's broadcast schedule or watching the episode to identify which matches appear.

**Critical Use Case:** Fixture validation during OCR (see [Business Rules](business_rules.md#rule-2-episode-manifest-constraint)).

#### Expected Matches
**Definition:** List of fixture IDs that appear in a specific MOTD episode.

**Format:** Each ID is `YYYY-MM-DD-hometeam-awayteam` (e.g., `2025-11-01-liverpool-astonvilla`)

**Purpose:** Constrain OCR team matching to only teams playing in this episode.

**Benefits:**
1. **Reduces false positives** - OCR won't match teams from replays/promos of other matches
2. **Improves accuracy** - Search space reduced from 20 PL teams → ~14 teams (7 matches)
3. **Confidence boost** - Teams in expected_matches get +10% confidence

**Example:**
If `expected_matches` contains `liverpool-astonvilla`, OCR can confidently match:
- "Liverpool" or "Aston Villa" as valid detections
- Reject "Manchester United" (not playing this gameweek)

**See Also:** [Business Rule #2](business_rules.md#rule-2-episode-manifest-constraint)

#### Fixture
**Definition:** A single Premier League match between two teams on a specific date.

**Format:** `YYYY-MM-DD-hometeam-awayteam`

**Example:** `2025-11-01-liverpool-astonvilla` (Liverpool vs Aston Villa at Anfield, 1 Nov 2025)

**Key Properties:**
- Home team (first in ID)
- Away team (second in ID)
- Match date
- Final score (added post-match)
- Kickoff time

**Data File:** `data/fixtures/premier_league_2025_26.json`

**Relationship to Episodes:** Each episode shows a subset of fixtures from a gameweek. Not all fixtures appear (broadcast rights restrictions).

#### Running Order
**Definition:** The editorial sequence in which MOTD chose to broadcast matches. **NOT chronological by kickoff time.**

**Format:** Numbered 1 (first shown) through 7 (last shown)

**Why It Matters:**
- **Primary research question:** "Are certain teams consistently shown first/last?"
- Potential bias indicator (e.g., "big six" always shown early)
- Reflects editorial decisions (most exciting match first, not earliest kickoff)

**Example:**
Matches played on 2025-11-01 (all kicked off at 15:00):
```
Kickoff Order (chronological):  Running Order (editorial):
1. Liverpool vs Aston Villa     1. Liverpool vs Aston Villa (chosen as lead)
2. Burnley vs Arsenal            2. Chelsea vs Newcastle (exciting match)
3. Chelsea vs Newcastle          3. Burnley vs Arsenal
4. Man City vs Southampton       4. Wolves vs Nottm Forest
5. West Ham vs Brighton          5. Man City vs Southampton
6. Wolves vs Nottm Forest        6. West Ham vs Brighton
7. Fulham vs Brentford          7. Fulham vs Brentford (least interesting)
```

**Critical Requirement:** 100% running order accuracy needed before downstream analysis (see [Business Rule #4](business_rules.md#rule-4-100-running-order-accuracy-requirement)).

#### Ground Truth
**Definition:** Manually verified data obtained by watching the full episode, used as validation reference.

**Types of Ground Truth Data:**
1. **Running order** - Actual match sequence in broadcast
2. **Segment timings** - Start/end timestamps for each segment type
3. **FT graphic locations** - Frame numbers where FT graphics appear
4. **Match boundaries** - Timestamps where one match ends and next begins

**How It's Created:** Human reviewer watches entire episode and records:
- When each match starts/ends (to the second)
- Which segments belong to which match
- Where key visual markers (FT graphics) appear

**Why It's Essential:**
- Pipeline validation (did OCR/classifier produce correct results?)
- Accuracy measurement (running order: 7/7 correct?)
- Edge case identification (missed FT graphics, boundary errors)

**Data File:** Ground truth stored in episode manifest or dedicated validation files.

---

### Segment Types

MOTD episodes are divided into 4 segment types for analysis. Each match typically has all 4 segments in sequence.

#### `studio_intro`
**Definition:** Host (Gary Lineker) introducing the next match from the studio before highlights begin.

**Typical Duration:** 7-11 seconds

**Characteristics:**
- Studio setting (not match footage)
- Host speaking directly to camera
- Match graphic displayed (team badges, final score)
- Preview of upcoming highlights
- NO scoreboard OCR (studio footage)

**Example Transcript:** "And now to Anfield, where Liverpool took on Aston Villa..."

**Why It Matters:** Counts towards total airtime for a match but is distinct from highlights duration.

#### `highlights`
**Definition:** Edited match footage with commentary, showing goals and key moments.

**Typical Duration:** 5-10 minutes (varies by match importance)

**Characteristics:**
- Match footage from broadcast feed
- Scoreboard OCR consistently present in top-left
- Commentary describing action
- Multiple camera angles
- Longest segment type

**Why Duration Varies:**
- More goals = longer highlights (more replays)
- Controversial incidents = extended coverage (VAR reviews, red cards)
- "Big six" matches typically get 8-10 minutes
- Lower-table matches may get only 5-6 minutes

**Detection Signal:** Scoreboard presence is definitive indicator (OCR in top-left corner).

#### `interviews`
**Definition:** Post-match interviews with players or managers, conducted pitch-side or in tunnel.

**Typical Duration:** 45-90 seconds

**Characteristics:**
- Interview subject in frame (player/manager)
- Team branding visible (training kit, stadium backdrop)
- Direct quotes from match participants
- Often immediately after highlights, before studio analysis
- NO scoreboard OCR (not match footage)

**Example Subjects:**
- Match-winning goalscorer
- Losing manager (if controversial defeat)
- Player of the match

**Why It Matters:** Measures access to players (do some teams get more interview time?).

#### `studio_analysis`
**Definition:** Pundits (e.g., Alan Shearer, Ian Wright) discussing match highlights from the studio.

**Typical Duration:** 2-5 minutes (varies by match importance)

**Characteristics:**
- Studio setting (panel discussion)
- Replay clips shown with pundit commentary
- Tactical analysis, player assessments
- NO scoreboard OCR (studio footage, not live match)
- Often dissects key moments (goals, controversies)

**Why Duration Varies:**
- Controversial incidents get extended debate (VAR decisions, red cards)
- Tactical masterclasses get detailed breakdown
- One-sided matches get brief analysis ("dominant performance, next match")

**Why It Matters:** Core research question - "Do some teams get more pundit discussion than others?"

**Detection Challenge:** Hardest segment type to classify (studio footage + match replays mixed).

---

### Pipeline Concepts

#### Scene
**Definition:** Continuous sequence of frames with similar visual content, detected algorithmically via PySceneDetect.

**Detection Method:** ContentDetector analyzes frame-to-frame differences:
- Threshold: 27.0 (default, works well for MOTD edits)
- Scene change = abrupt visual transition (cut, dissolve, wipe)

**Typical Causes of Scene Changes:**
- Camera angle switch during match
- Cut from studio to highlights
- Transition to interview or analysis
- Replay shown from different angle

**Example:**
```
Scene 1: Studio intro (frames 1-250, 10 seconds)
  └─ Scene change detected at frame 251
Scene 2: Highlights - wide angle (frames 251-450, 8 seconds)
  └─ Scene change detected at frame 451
Scene 3: Highlights - close-up (frames 451-620, 7 seconds)
```

**Why Scene Detection Matters:**
- Reduces frames to analyze (only sample 1 frame per scene, not all 162,000)
- Natural segmentation boundaries (scenes often align with segment transitions)
- Performance optimization (4,500 scenes vs 162,000 frames for 90-min episode)

**Limitation:** Not all scene changes = segment boundaries (camera switches within highlights create scenes).

#### Frame
**Definition:** Single image extracted from video at a specific timestamp for OCR analysis.

**Format:** JPEG image, 1280×720 resolution (downscaled from 1920×1080 for performance)

**Naming Convention:** `frame_{index}_{type}_{timestamp}s.jpg`
- `frame_0329_scene_change_607.3s.jpg` (frame 329, scene change at 607.3 seconds)
- `frame_1024_interval_2040.0s.jpg` (frame 1024, interval sample at 2040.0 seconds)

**Extraction Strategy:** Hybrid approach (see [Visual Patterns](visual_patterns.md))
1. **Scene changes** - First frame after each detected scene change
2. **Interval sampling** - Every 2.0 seconds (to catch missed FT graphics)

**Why Both?**
- Scene changes alone miss short FT graphics (< 1 second visibility)
- Interval sampling alone creates too many frames (162,000 → 2,700)
- Hybrid captures both scene boundaries AND ensures coverage

**Typical Episode:** 2,500-2,700 frames extracted from 90-minute video.

#### OCR Region
**Definition:** Bounding box coordinates defining where specific visual elements appear in frames.

**Format:** `[x, y, width, height]` in pixels

**Calibrated for:** 720p resolution (1280×720) - MUST adjust if video resolution differs

**Standard Regions (see `config/config.yaml`):**
```yaml
ocr_regions:
  ft_score:           [320, 200, 640, 200]   # Centre of frame (FT graphics)
  scoreboard:         [20, 20, 300, 80]      # Top-left corner (live score)
  formation_header:   [400, 50, 480, 100]    # Top-centre (team names in formation)
```

**Why Regions Matter:**
- **Performance:** OCR on full frame wastes compute (95% is pitch, irrelevant)
- **Accuracy:** Focused regions reduce false positives (e.g., crowd banners with text)
- **Speed:** 200×640 region is 10× faster than full 1280×720 frame

**Calibration Process:**
1. Extract sample frames with known visual elements
2. Manually identify bounding boxes in image editor
3. Test OCR accuracy on region
4. Adjust if resolution changes (e.g., BBC switches to 1080p)

**IMPORTANT:** Always verify video resolution with `ffprobe` before assuming 720p coordinates are correct.

---

## Data Relationships

### Overall Structure

```
Premier League Season (2025/26)
    ├── 20 Teams (data/teams/premier_league_2025_26.json)
    │   ├── Liverpool
    │   ├── Arsenal
    │   ├── Manchester City
    │   └── ... (17 more)
    │
    ├── 380 Fixtures across season (data/fixtures/premier_league_2025_26.json)
    │   ├── Gameweek 1 (10 matches)
    │   ├── Gameweek 2 (10 matches)
    │   └── ... (36 more gameweeks)
    │
    └── MOTD Episodes (~38 episodes, one per Saturday)
        └── Episode: motd_2025-26_2025-11-01
            ├── Broadcast Date: 2025-11-01
            ├── Expected Matches: 7 fixture IDs (subset of Saturday's 10 matches)
            │   ├── liverpool-astonvilla
            │   ├── burnley-arsenal
            │   ├── chelsea-newcastle
            │   ├── manchester_city-southampton
            │   ├── west_ham-brighton
            │   ├── wolves-nottingham_forest
            │   └── fulham-brentford
            │
            └── Running Order: Editorial sequence (manual ground truth)
                ├── 1st: Liverpool vs Aston Villa (most exciting)
                ├── 2nd: Chelsea vs Newcastle
                ├── 3rd: Burnley vs Arsenal
                ├── 4th: Wolves vs Nottingham Forest
                ├── 5th: Manchester City vs Southampton
                ├── 6th: West Ham vs Brighton
                └── 7th: Fulham vs Brentford (least interesting)
```

### Episode → Fixtures → Teams Flow

**Step 1: Identify Episode**
```
Episode ID: motd_2025-26_2025-11-01
Data file: data/episodes/episode_manifest.json
```

**Step 2: Load Expected Matches**
```
Expected matches for this episode (7 out of 10 Saturday fixtures):
- liverpool-astonvilla
- burnley-arsenal
- chelsea-newcastle
- manchester_city-southampton
- west_ham-brighton
- wolves-nottingham_forest
- fulham-brentford

NOT included (broadcast elsewhere):
- tottenham-everton (Sky Sports)
- leicester-ipswich (TNT Sports)
- bournemouth-manchester_united (Amazon Prime)
```

**Step 3: Load Fixture Details**
```
Fixture ID: liverpool-astonvilla
Data file: data/fixtures/premier_league_2025_26.json

Details:
- Home team: Liverpool
- Away team: Aston Villa
- Date: 2025-11-01
- Kickoff: 15:00
- Final score: 2-0
```

**Step 4: OCR Validation**
```
OCR detects: "Liverpool" in frame_0329

Validation process:
1. Is "Liverpool" in expected_matches teams?
   → Yes (liverpool-astonvilla)
2. Confidence boost: +10% (fixture-aware validation)
3. Expected opponent: Aston Villa
4. If second team detected, verify it's "Aston Villa"
5. If only "Liverpool" detected, infer opponent from fixture
```

### Why Episode Manifest Exists

**Problem:** MOTD doesn't show all Premier League matches.

**Background:**
- 10 matches typically played on Saturday (main MOTD broadcast day)
- BBC has rights to ~7 matches per gameweek
- Sky Sports, TNT Sports, Amazon Prime show the others
- BBC selects 7 "best" matches (by fan interest, goals scored, etc.)

**Solution:** Episode manifest defines which 7 fixtures appear in each episode.

**Impact on Pipeline:**
1. **OCR validation** - Only accept teams from expected_matches (reduces false positives)
2. **Fixture matching** - Search space reduced from 20 teams → ~14 teams (7 matches)
3. **Confidence scoring** - Teams in expected_matches get higher confidence
4. **Opponent inference** - Can infer missing team from fixture pairing

**Example False Positive Prevention:**
```
Scenario: OCR detects "Manchester United" in frame

Check 1: Is "Manchester United" in expected_matches?
- No (they're playing on Sky Sports this week)

Check 2: Could this be a replay/promo?
- Possibly (MOTD sometimes shows clips from other matches)

Action: Flag as low-confidence detection, require additional validation
- Is "FT" text present? (if yes, might be MOTD2 clip)
- Is opponent also detected? (if yes, verify pairing exists in fixtures)
```

**Without Episode Manifest:**
- OCR would accept "Manchester United" as valid (they're a PL team)
- Incorrect match assignment (United aren't playing in this episode)
- Running order corrupted (8 matches detected instead of 7)

---

## Key Workflows

### Workflow 1: OCR Fallback Strategy

When processing a frame to detect teams and scores:

```
┌─────────────────────────────────────────────────┐
│ Frame Input (e.g., frame_0329_scene_change_607.3s) │
└─────────────────────────────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────┐
    │ Step 1: Try to Extract FT Graphic      │
    │ Region: ft_score [320, 200, 640, 200]  │
    └────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
         YES                   NO
          │                     │
          ▼                     ▼
  ┌───────────────────┐  ┌──────────────────────────────┐
  │ Valid FT Graphic? │  │ Step 2: Try Extract Scoreboard│
  │ - 2 teams         │  │ Region: scoreboard [20,20...]│
  │ - Score present   │  └──────────────────────────────┘
  │ - "FT" text       │                 │
  └───────────────────┘      ┌──────────┴─────────┐
          │                  │                    │
          │                 YES                  NO
          │                  │                    │
          │                  ▼                    ▼
          │          ┌──────────────────┐  ┌─────────────────────┐
          │          │ Valid Scoreboard?│  │ Step 3: Try Opponent│
          │          │ - 1-2 teams      │  │ Inference           │
          │          │ - Score pattern  │  │ - 1 team detected?  │
          │          └──────────────────┘  │ - Lookup fixture    │
          │                  │             └─────────────────────┘
          │                  │                       │
          │                  │             ┌─────────┴────────┐
          │                  │            YES               NO
          │                  │             │                 │
          │                  │             ▼                 ▼
          │                  │    ┌────────────────┐  ┌──────────┐
          │                  │    │ Infer Opponent │  │   SKIP   │
          │                  │    │ from Fixtures  │  │  FRAME   │
          │                  │    │ Confidence:0.75│  └──────────┘
          │                  │    └────────────────┘
          │                  │             │
          ▼                  ▼             ▼
    ┌──────────────────────────────────────────┐
    │         Return ProcessedScene            │
    │                                          │
    │ FT Graphic:  Confidence = 0.95          │
    │ Scoreboard:  Confidence = 0.80          │
    │ Inferred:    Confidence = 0.75          │
    └──────────────────────────────────────────┘
```

**Confidence Levels by Source:**
- **FT Graphic:** 0.95 (gold standard - clean text, static, both teams visible)
- **Scoreboard:** 0.80 (fallback - motion blur, smaller text, partial visibility)
- **Opponent Inference:** 0.75 (derived - one team OCR'd, other inferred from fixture)
- **Formation:** 0.70 (lowest - no score validation, single team visible)

**Why This Order:**
1. FT graphics are most reliable (static, clean, complete information)
2. Scoreboards are available throughout highlights (fallback for missed FT graphics)
3. Opponent inference leverages fixture knowledge (better than skipping frame)

**Edge Cases:**
- If FT validation passes but only 1 team detected → Use opponent inference
- If scoreboard detected but duration < 60s → Flag as potential false positive
- If no teams detected after all 3 steps → Skip frame (insufficient data)

---

### Workflow 2: Fixture-Aware Team Matching

When OCR extracts text from a frame:

```
┌──────────────────────────────────────┐
│ OCR Extracted Text: "Liverpool 2 0"  │
└──────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │ Step 1: Fuzzy Match Teams     │
    │ - Split text into tokens      │
    │ - Match against PL team list  │
    │ - RapidFuzz similarity > 85%  │
    └───────────────────────────────┘
                │
                ▼
        ┌───────────────────┐
        │ Match: "Liverpool"│
        │ Confidence: 0.92  │
        └───────────────────┘
                │
                ▼
    ┌─────────────────────────────────────┐
    │ Step 2: Fixture Validation          │
    │ - Load episode expected_matches     │
    │ - Is "Liverpool" in any fixture?    │
    └─────────────────────────────────────┘
                │
        ┌───────┴────────┐
       YES              NO
        │                │
        ▼                ▼
┌───────────────────┐  ┌──────────────────────────┐
│ Fixture Found:    │  │ Flag as Potential Error: │
│ liverpool-        │  │ - Not in expected_matches│
│ astonvilla        │  │ - Could be replay/promo  │
│                   │  │ - Lower confidence       │
│ Confidence: +10%  │  └──────────────────────────┘
│ → 0.92 + 0.10     │
│ = 1.0 (capped)    │
└───────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ Step 3: Opponent Lookup                 │
│ - Fixture: liverpool-astonvilla         │
│ - Expected opponent: "Aston Villa"      │
│ - Check if second team detected in OCR  │
└─────────────────────────────────────────┘
        │
    ┌───┴────┐
   YES       NO
    │         │
    ▼         ▼
┌────────────────┐  ┌──────────────────────┐
│ Verify Match:  │  │ Infer Opponent:      │
│ - Is 2nd team  │  │ - Only 1 team in OCR │
│   "Aston Villa"│  │ - Add "Aston Villa"  │
│ - Confidence:  │  │ - Confidence: 0.75   │
│   0.95 (both   │  │ - Mark as inferred   │
│   teams OCR'd) │  └──────────────────────┘
└────────────────┘
```

**Benefits of Fixture-Aware Matching:**
1. **Reduced false positives** - Rejects teams not in this episode
2. **Confidence boost** - Expected teams get +10% confidence
3. **Opponent inference** - Can complete partial OCR results
4. **Validation** - Verifies team pairings match actual fixtures

**Example 1: Successful Validation**
```
OCR: "Liverpool" + "Aston Villa" detected
Fixture check: liverpool-astonvilla exists in expected_matches ✓
Result: Both teams confirmed, confidence = 0.95
```

**Example 2: Opponent Inference**
```
OCR: "Liverpool" detected, second team missing (non-bold font)
Fixture check: liverpool-astonvilla exists in expected_matches ✓
Infer opponent: "Aston Villa" (from fixture pairing)
Result: Liverpool (OCR'd, 0.92) + Aston Villa (inferred, 0.75)
```

**Example 3: Invalid Team Detected**
```
OCR: "Manchester United" detected
Fixture check: No fixture with Man Utd in expected_matches ✗
Result: Flag as potential false positive (replay/promo?)
Action: Require additional validation (FT text, score, etc.)
```

---

### Workflow 3: Segment Classification (Multi-Signal)

When classifying a scene into one of 4 segment types:

```
┌──────────────────────────────────┐
│ Scene Input (e.g., Scene #47)    │
│ Duration: 8.3 seconds            │
│ Frames: 249 frames (30fps)       │
└──────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────┐
│ Signal 1: OCR Scoreboard Detection       │
│ - Run OCR on sample frames               │
│ - Check scoreboard region [20,20,300,80] │
└──────────────────────────────────────────┘
              │
      ┌───────┴────────┐
     YES              NO
      │                │
      ▼                ▼
┌──────────────┐  ┌────────────────────────────────┐
│ HIGHLIGHTS   │  │ Signal 2: Transcript Analysis  │
│ (definitive) │  │ - Extract words for this scene │
│              │  │ - Count team name mentions     │
│ Scoreboard = │  └────────────────────────────────┘
│ match footage│                 │
└──────────────┘       ┌─────────┴─────────┐
                       │                   │
              High mentions (>5)    Low mentions (<2)
                       │                   │
                       ▼                   ▼
            ┌────────────────────┐  ┌──────────────────┐
            │ Signal 3: Duration │  │ Signal 3: Duration│
            │ - 45-90s?          │  │ - 7-11s?         │
            └────────────────────┘  └──────────────────┘
                       │                   │
                  ┌────┴─────┐        ┌────┴─────┐
                 YES        NO       YES        NO
                  │          │        │          │
                  ▼          ▼        ▼          ▼
          ┌──────────┐  ┌─────────────┐  ┌─────────────┐
          │INTERVIEWS│  │STUDIO       │  │STUDIO       │
          │          │  │ANALYSIS     │  │INTRO        │
          │Brief     │  │(2-5 min,    │  │(7-11s,      │
          │quotes    │  │team         │  │preview)     │
          │from      │  │discussion)  │  └─────────────┘
          │players   │  └─────────────┘
          └──────────┘
```

**Signal Priority (Hierarchical Decision Tree):**

1. **OCR Scoreboard** (highest priority)
   - If scoreboard detected → `highlights` (definitive)
   - Scoreboard only appears during match footage

2. **Transcript Team Mentions** (medium priority)
   - High mentions (>5 per minute) → `studio_analysis` or `highlights`
   - Low mentions (<2 per minute) → `studio_intro` or `interviews`

3. **Duration Pattern** (lowest priority, tie-breaker)
   - 7-11 seconds → `studio_intro`
   - 45-90 seconds → `interviews`
   - 2-5 minutes → `studio_analysis`
   - 5-10 minutes → `highlights` (if scoreboard missed)

**Example Classifications:**

**Scene A:**
- OCR: Scoreboard detected ✓
- Duration: 6.2 minutes
- Classification: **`highlights`** (scoreboard is definitive)

**Scene B:**
- OCR: No scoreboard
- Transcript: "Liverpool", "Salah", "goal" (8 team mentions)
- Duration: 3.1 minutes
- Classification: **`studio_analysis`** (high mentions + medium duration)

**Scene C:**
- OCR: No scoreboard
- Transcript: "Now to Anfield" (1 team mention)
- Duration: 9 seconds
- Classification: **`studio_intro`** (low mentions + short duration)

**Scene D:**
- OCR: No scoreboard
- Transcript: "Klopp" interview quotes (4 mentions)
- Duration: 72 seconds
- Classification: **`interviews`** (medium mentions + interview duration)

**Edge Cases:**
- Scoreboard detected but duration < 60s → Flag as error (highlights never this short)
- High team mentions but duration > 10 min → Likely multiple scenes merged, re-check scene detection
- No scoreboard + ambiguous signals → Default to `studio_analysis` (most common non-highlights segment)

---

## Related Documentation

### Business Rules
See [business_rules.md](business_rules.md) for detailed processing rules:
- FT Graphic Validation
- Episode Manifest Constraint
- Opponent Inference Logic
- Running Order Accuracy Requirements
- Segment Classification Hierarchy

### Visual Patterns
See [visual_patterns.md](visual_patterns.md) for:
- MOTD episode structure (intro → matches → closing)
- Visual element screenshots (FT graphics, scoreboards, formations)
- Typical segment durations
- Ground truth timeline for reference episode

### Code References
Key source files implementing domain logic:
- `src/motd/ocr/reader.py` - OCR extraction and validation
- `src/motd/ocr/team_matcher.py` - Fuzzy team matching
- `src/motd/ocr/fixture_matcher.py` - Fixture-aware validation
- `src/motd/ocr/scene_processor.py` - Multi-source fallback logic
- `src/motd/pipeline/models.py` - Pydantic domain models

---

**Last Updated:** 2025-11-18 (Task 011b-2 domain documentation initiative)
