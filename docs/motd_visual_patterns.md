# Match of the Day - Visual Pattern Documentation

**Episode:** motd_2025-26_2025-11-01
**Date Created:** 2025-11-11
**Purpose:** Document recurring visual patterns in MOTD to guide OCR implementation

---

## Episode Timeline

### Overview
| Segment Type | Start Time | End Time | Duration | Notes |
|-------------|------------|----------|----------|-------|
| Intro Sequence | 00:00:00 | XX:XX:XX | ~X min | Standard MOTD intro |
| Match 1 | XX:XX:XX | XX:XX:XX | ~X min | [Team A] vs [Team B] |
| Studio Analysis 1 | XX:XX:XX | XX:XX:XX | ~X min | Post-match discussion |
| Match 2 | XX:XX:XX | XX:XX:XX | ~X min | [Team C] vs [Team D] |
| Studio Analysis 2 | XX:XX:XX | XX:XX:XX | ~X min | |
| Match 3 | XX:XX:XX | XX:XX:XX | ~X min | |
| ... | | | | Continue pattern |
| Outro | XX:XX:XX | XX:XX:XX | ~X min | Credits/next week preview |

### Key Timecodes
- **Intro ends / First match starts:** XX:XX:XX
- **Final match ends:** XX:XX:XX
- **Total episode duration:** XX:XX:XX

### Running Order (Matches)
1. [Team A] vs [Team B] - starts at XX:XX:XX
2. [Team C] vs [Team D] - starts at XX:XX:XX
3. [Team E] vs [Team F] - starts at XX:XX:XX
4. ... (continue for all matches)

---

## Visual Patterns by Type

### 1. Intro Sequence
**Visual characteristics:**
- [Describe what the intro looks like]
- [Music, graphics, animations]

**Duration:** ~XX seconds (typically consistent across episodes)

**Auto-extracted frames showing intro:**
- scene_XXX.jpg - [brief description]
- scene_XXX.jpg - [brief description]

**Notes for OCR:**
- Can skip first ~XX seconds of every episode (no team graphics in intro)
- Intro is identical week-to-week (could detect and skip automatically)

---

### 2. Formation Graphics
**Visual characteristics:**
- **Location on screen:** [e.g., bottom-right corner, full bottom third, etc.]
- **Text colour:** [e.g., white, yellow]
- **Background:** [e.g., semi-transparent dark overlay, team colour gradient]
- **Font style:** [e.g., BBC Sport font, bold, uppercase]
- **Additional elements:** [e.g., club badges, player names, formation diagram]

**When they appear:**
- [e.g., at start of match highlights during team walkout]
- [e.g., before kickoff]
- **Typical duration visible:** ~X seconds

**Auto-extracted frames showing formation graphics:**
- scene_XXX.jpg - [Team A] vs [Team B] formation (timestamp XX:XX:XX)
- scene_XXX.jpg - [Team C] vs [Team D] formation (timestamp XX:XX:XX)
- scene_XXX.jpg - [another example]

**Text examples visible in graphics:**
- [e.g., "BRIGHTON & HOVE ALBION" or "Brighton" or "BRIGHTON"]
- [e.g., "LEEDS UNITED" or "Leeds" or "LEEDS"]
- [Note any abbreviations or variations used]

**Notes for OCR:**
- These are the HIGHEST QUALITY frames for team detection
- Text is static, clear, well-contrasted
- Should prioritise these frames over scoreboard graphics
- OCR region should focus on [specific area description]

---

### 3. Scoreboard Graphics
**Visual characteristics:**
- **Location on screen:** [e.g., top-left corner]
- **Text colour:** [e.g., white on dark background]
- **Background:** [e.g., BBC Sport red bar, semi-transparent]
- **Additional elements:** [e.g., score, match time, BBC Sport logo]

**When they appear:**
- [e.g., during match highlights, constantly visible]
- [e.g., updated when goals scored]

**Auto-extracted frames showing scoreboard graphics:**
- scene_XXX.jpg - [Team A] vs [Team B] scoreboard (timestamp XX:XX:XX)
- scene_XXX.jpg - [example during play]
- scene_XXX.jpg - [example with different teams]

**Text examples visible in scoreboards:**
- [e.g., "Brighton 2-0 Leeds" or "BHA 2 LEE 0"]
- [Note any abbreviations used]

**Notes for OCR:**
- Lower quality than formation graphics (often motion-blurred)
- May be partially obscured by on-screen graphics or player overlays
- Use as secondary source if formation graphics not available
- OCR region should be [specific coordinates/area]

---

### 4. Studio Segments
**Visual characteristics:**
- **Layout:** [e.g., presenters at desk, analysis screens behind]
- **Colour palette:** [e.g., dark blue set, BBC Sport branding]
- **Typical presenters:** [e.g., Gary Lineker, pundits]

**When they appear:**
- [e.g., between matches, post-match analysis]
- **Typical duration:** ~X-XX minutes

**Auto-extracted frames showing studio:**
- scene_XXX.jpg - [description, e.g., presenter intro]
- scene_XXX.jpg - [post-match discussion]

**Notes for OCR:**
- NO team graphics visible (skip these frames for OCR)
- Can identify studio segments by [colour palette, layout, etc.]
- Could filter out before OCR to save processing time

---

### 5. Transition Patterns
**How MOTD transitions between segments:**

**Match → Studio:**
- [Describe transition, e.g., fade to black, cut, graphic animation]
- Auto-extracted frame example: scene_XXX.jpg

**Studio → Match:**
- [Describe transition]
- Auto-extracted frame example: scene_XXX.jpg

**Match Highlights Internal Structure:**
1. [e.g., Team walkout with formation graphic]
2. [e.g., Kickoff]
3. [e.g., Match action with scoreboard]
4. [e.g., Goals/key moments]
5. [e.g., Full-time whistle]

**Notes for OCR:**
- Transitions help identify segment boundaries
- Formation graphics typically appear at [specific point in match sequence]
- Can use transition detection to find formation graphics more efficiently

---

## OCR Implementation Recommendations

### Priority 1: Formation Graphics (Highest Accuracy)
- **Target frames:** [list scene numbers that show formation graphics]
- **Recommended OCR region:** [coordinates or description]
- **Expected accuracy:** >95% (text is clear and static)

### Priority 2: Scoreboard Graphics (Backup Method)
- **Target frames:** [during match highlights]
- **Recommended OCR region:** [coordinates or description]
- **Expected accuracy:** ~85-90% (motion blur, obscuring)

### Priority 3: Skip These Frames
- **Intro:** scene_XXX to scene_XXX (first ~XX seconds)
- **Studio:** [characteristics to identify studio frames]
- **Transitions:** [very short duration scenes, e.g., <1 second]

### Scene Filtering Strategy
Based on this reconnaissance, suggest filtering 810 scenes to ~XXX relevant scenes by:
1. Skip first ~XX scenes (intro)
2. Skip scenes with duration <X seconds (transitions)
3. Skip scenes that match studio visual pattern
4. Prioritise scenes around [timing when formation graphics appear]

**Estimated scenes for OCR after filtering:** ~XXX out of 810

---

## Manual Annotations (Optional)

If any critical patterns aren't captured in auto-extracted frames, add manual screenshots below:

### [Pattern Name]
![Manual screenshot](path/to/manual/screenshot.png)
- **Timestamp:** XX:XX:XX
- **Description:** [what this shows]
- **Why needed:** [why auto-extracted frames didn't capture this]

---

## Questions for OCR Implementation

After completing this reconnaissance, answer these questions for 009b-009g:

1. **Should we skip the intro entirely?** YES / NO
   - If YES, skip first XX seconds

2. **What's the best frame type for OCR?** Formation graphics / Scoreboards / Both
   - Justification: [based on your observations]

3. **Can we identify studio segments visually?** YES / NO
   - If YES, how? [colour palette, layout, etc.]

4. **Estimated % of 810 frames that are useful for OCR:** XX%
   - Filtering strategy: [describe approach]

5. **Any unexpected patterns discovered:**
   - [anything not anticipated in planning]

---

## Completion Checklist

- [ ] Episode timeline table completed
- [ ] Formation graphics section documented with frame examples
- [ ] Scoreboard graphics section documented with frame examples
- [ ] Studio segments section documented with frame examples
- [ ] Transition patterns described
- [ ] OCR recommendations section completed
- [ ] Questions section answered
- [ ] Ready to proceed to 009b (OCR implementation)
