# Sub-Task Documentation Template

**Purpose:** This template provides a standard structure for all sub-task documentation files. Use this pattern to ensure sub-tasks have consistent context and are easy to understand.

---

## Template Structure

```markdown
# Task XXX-Y: [Task Name]

## Quick Context

**Parent Task:** [Link to epic/parent README, e.g., `../XXX-epic-name/README.md`]
**Domain Concepts:** [List key terms with links to glossary, e.g., `../../domain/README.md#concept-name`]
**Business Rules:** [Link to relevant business rules, e.g., `../../domain/business_rules.md#rule-name`]

**Why This Matters:** [1-3 sentences explaining business value and how this sub-task contributes to the overall goal]

[Optional: **Key Insight** or **Critical Requirement** - Highlight important context that impacts implementation]

See [Visual Patterns](../../domain/visual_patterns.md) [or other relevant docs] for [specific reference].

---

## Objective
[Clear, focused statement of what this sub-task aims to accomplish]

## Prerequisites
- [ ] [Previous task or dependency]
- [ ] [Required data files or knowledge]
- [ ] [Domain knowledge required - link to relevant glossary section]

## Estimated Time
[Time estimate]

## [Implementation/Success Criteria/etc.]
[Rest of sub-task content follows standard structure...]
```

---

## Section-by-Section Guidance

### Quick Context Section (REQUIRED)

**Purpose:** Provide immediate context so readers understand:
1. Where this task fits in the larger system
2. What domain knowledge they need
3. Why this task matters (business value)

**Parent Task:**
- Link to the epic or parent task README
- Example: `[009-ocr-implementation](../009-ocr-implementation/README.md)`
- Helps readers understand the bigger picture

**Domain Concepts:**
- List 2-5 key domain terms used in this task
- Link each to the glossary definition: `[FT Graphic](../../domain/README.md#ft-graphic)`
- Focus on terms that might be unclear to someone unfamiliar with MOTD domain

**Business Rules:**
- Link to relevant business rules that govern this task's implementation
- Example: `[FT Graphic Validation](../../domain/business_rules.md#rule-1-ft-graphic-validation)`
- Only include rules that directly impact this sub-task

**Why This Matters:**
- 1-3 sentences explaining business value
- Connect to research questions or user goals
- Example: "FT graphics are the gold standard for team detection because they provide both teams, score validation, and match boundary markers in a single static frame. Reliable FT detection is critical for 100% running order accuracy."

**Optional Callouts:**
- **Key Insight:** Highlight a non-obvious pattern or constraint
- **Critical Requirement:** Emphasize a strict requirement (e.g., "100% accuracy required")
- **Key Data:** Point to a data file or structure that's essential (e.g., episode manifest)

**Related Documentation:**
- Link to visual patterns, architecture docs, or other references
- Example: `See [Visual Patterns](../../domain/visual_patterns.md) for FT graphic screenshots and timing.`

---

### Objective Section

**Purpose:** Single clear statement of what this sub-task achieves.

**Good Example:**
```markdown
## Objective
Implement FT graphic validation logic to filter out false positives (possession bars, formation graphics) and ensure only genuine full-time score graphics are accepted for team detection.
```

**Bad Example:**
```markdown
## Objective
Add validation.
```

**Guidelines:**
- Start with an action verb (Implement, Create, Extract, Validate, etc.)
- Be specific about WHAT is being built
- Include WHY if not obvious (to filter false positives)
- Keep it to 1-2 sentences

---

### Prerequisites Section

**Purpose:** Ensure readers have completed dependencies and understand required knowledge.

**Structure:**
```markdown
## Prerequisites
- [ ] Task XXX-Y complete (brief description)
- [ ] Data file available: `data/path/to/file.json`
- [ ] Domain knowledge: [Concept Name](../../domain/README.md#concept-name)
```

**Guidelines:**
- Use checkboxes for trackable items
- Link to previous tasks
- Link to required domain knowledge (don't assume it's known)
- Include data file paths if specific files are needed

**Example:**
```markdown
## Prerequisites
- [x] Task 009c complete (team matcher implemented)
- [x] Episode manifest available: `data/episodes/episode_manifest.json`
- [ ] Domain knowledge: [Expected Matches](../../domain/README.md#expected-matches)
- [ ] Understand: [Fixture Validation](../../domain/business_rules.md#rule-2-episode-manifest-constraint)
```

---

### Estimated Time Section

**Purpose:** Set expectations for task duration.

**Format:**
```markdown
## Estimated Time
2-2.5 hours
```

**Guidelines:**
- Provide a range (accounts for variability)
- Include research, implementation, and testing
- If uncertain, err on the side of more time

---

### Implementation Steps / Success Criteria / etc.

**Purpose:** The detailed work breakdown.

**Guidelines:**
- Break into discrete, actionable steps
- Use checkboxes for trackable progress
- Include code examples where helpful
- Link to relevant domain docs or business rules when describing logic

**Example with Domain Links:**
```markdown
## Implementation Steps

### 1. Implement FT Validation Logic

Create validation method following [Business Rule #1](../../domain/business_rules.md#rule-1-ft-graphic-validation):

```python
def validate_ft_graphic(self, ocr_results, detected_teams):
    """
    Validate FT graphic per Rule #1:
    - ≥1 team detected (allows opponent inference)
    - Score pattern present (e.g., "2-1", "3 | 0")
    - "FT" text present
    """
    # Implementation...
```

See [FT Graphic](../../domain/README.md#ft-graphic) for visual examples.

### 2. Test Validation

- [ ] Test with ground truth FT graphics (all should pass)
- [ ] Test with possession bars (should reject - no "FT" text)
- [ ] Test with formation graphics (should reject - no score)
```

---

## When to Use Domain Links

**Link to Glossary When:**
- Introducing a domain-specific term for the first time
- Using jargon that might not be obvious (e.g., "running order", "expected matches")
- Referencing visual elements (FT graphic, scoreboard, formation)

**Link to Business Rules When:**
- Describing validation logic
- Explaining why certain decisions are made
- Implementing confidence scoring or thresholds

**Link to Visual Patterns When:**
- Discussing timing or duration patterns
- Referencing ground truth data
- Explaining segment structure

---

## Examples of Good Quick Context Sections

### Example 1: OCR-Focused Sub-Task

```markdown
## Quick Context

**Parent Task:** [009-ocr-implementation](../009-ocr-implementation/README.md)
**Domain Concepts:** [FT Graphic](../../domain/README.md#ft-graphic), [Scoreboard](../../domain/README.md#scoreboard), [OCR Region](../../domain/README.md#ocr-region)
**Business Rules:** [FT Graphic Validation](../../domain/business_rules.md#rule-1-ft-graphic-validation)

**Why This Matters:** FT graphics are the gold standard for team detection (95%+ accuracy) because they're static, have clean text, and show both teams + score + "FT" label in a single frame. Reliable FT detection is critical for achieving 100% running order accuracy.

**Key Insight:** BBC's FT graphics use pipe character `|` for score separator (e.g., "2 | 0"), but OCR often misreads it as hyphen `-` or space. Validation must handle all variants.

See [Visual Patterns](../../domain/visual_patterns.md) for FT graphic screenshots and timing examples.
```

### Example 2: Analysis-Focused Sub-Task

```markdown
## Quick Context

**Parent Task:** [011-analysis-pipeline](README.md)
**Domain Concepts:** [Segment Types](../../domain/README.md#segment-types), [Running Order](../../domain/README.md#running-order), [Ground Truth](../../domain/README.md#ground-truth)
**Business Rules:** [100% Running Order Accuracy](../../domain/business_rules.md#rule-4-100-running-order-accuracy-requirement)

**Why This Matters:** Running order is the editorial sequence MOTD chose to broadcast matches - NOT chronological. It's a potential bias indicator ("Are certain teams always shown first?"). 100% accuracy required because one wrong boundary corrupts 2+ matches.

**Critical Requirement:** If running order accuracy < 100%, STOP. Do not proceed to downstream tasks.

**Key Data:** Episode manifest defines expected matches - we know there are exactly 7 matches to detect (not 6, not 8).

See [Visual Patterns](../../domain/visual_patterns.md) for ground truth running order.
```

### Example 3: Data Processing Sub-Task

```markdown
## Quick Context

**Parent Task:** [010-transcription-pipeline](../010-transcription-pipeline/README.md)
**Domain Concepts:** [Episode](../../domain/README.md#episode), [Scene](../../domain/README.md#scene)
**Business Rules:** N/A (pure data processing task)

**Why This Matters:** Transcription provides team mentions for segment classification. Faster-whisper processes 90-minute videos in 3-4 minutes vs 10-15 minutes for standard Whisper (4x speedup with identical accuracy).

**CRITICAL:** Always use faster-whisper, not openai-whisper. Check cache before transcribing - it's the slowest pipeline stage.

See [ML Pipeline Patterns](../../../.claude/commands/references/ml_pipeline_patterns.md) for caching implementation.
```

---

## Anti-Patterns to Avoid

### ❌ Missing Context
```markdown
# Task 009d: Implement Fixture Matcher

## Objective
Validate OCR results against fixtures.

## Implementation Steps
1. Load fixtures
2. Match teams
3. Return results
```

**Problem:** No explanation of what fixtures are, why validation is needed, or where the data comes from.

### ❌ Assumed Knowledge
```markdown
**Why This Matters:** We need fixture validation for expected_matches.
```

**Problem:** Assumes reader knows what "expected_matches" means. Should link to glossary.

### ❌ Duplicate Information
```markdown
## Quick Context

**FT Graphic Definition:** A full-time score graphic shows final score with both team names at the end of match highlights. Appears for 2-4 seconds. Clean text. Both teams visible. Score prominently displayed. "FT" label present.

[...continues for 3 more paragraphs duplicating the glossary...]
```

**Problem:** Duplicates glossary content instead of linking to it. If definition changes, must update in multiple places.

### ❌ Missing Business Rule Link
```markdown
## Validation Logic

FT graphics must have:
- 2 teams
- Score
- "FT" text

If not, reject the frame.
```

**Problem:** This IS a business rule but doesn't link to the canonical definition. Should reference [Rule #1](../../domain/business_rules.md#rule-1-ft-graphic-validation).

---

## Checklist for Sub-Task Documentation

Before committing a sub-task file, verify:

- [ ] Quick Context section present
- [ ] Parent task linked
- [ ] Domain concepts listed and linked to glossary
- [ ] Business rules linked (if applicable)
- [ ] "Why This Matters" explains business value
- [ ] Related documentation linked (visual patterns, architecture, etc.)
- [ ] Prerequisites include domain knowledge requirements
- [ ] Implementation steps reference domain docs where relevant
- [ ] No duplicate glossary definitions (link instead)
- [ ] Technical jargon explained or linked

---

## Usage Notes

**When Creating New Sub-Tasks:**
1. Copy this template structure
2. Fill in Quick Context FIRST (forces you to think about prerequisites)
3. Link liberally to domain docs (err on the side of over-linking)
4. Test links to ensure they work (relative paths from task location)

**When Updating Existing Sub-Tasks:**
1. Add Quick Context section at top (after title, before Objective)
2. Review implementation steps for domain terminology
3. Add links to glossary/business rules where terms are used
4. Update prerequisites to include domain knowledge requirements

**For Epic/Parent Task READMEs:**
- Add "How It Works" section after Objective
- Explain business context and domain concepts for entire epic
- Sub-tasks can be more concise if parent README has good context

---

## Related Documentation

- [Domain Glossary](../../docs/domain/README.md) - Core terminology definitions
- [Business Rules](../../docs/domain/business_rules.md) - Validation and processing rules
- [Visual Patterns](../../docs/domain/visual_patterns.md) - MOTD episode structure
- [Code Quality Checklist](code_quality_checklist.md) - Code review standards
- [Testing Guidelines](testing_guidelines.md) - Test standards

---

**Last Updated:** 2025-11-18 (created during Task 011b-2 domain documentation initiative)
