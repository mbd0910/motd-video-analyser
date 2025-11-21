# Commit Message Style

All commits should be human-readable summaries **without conventional prefixes**

---

## Short Commits (Feature Branch Work)

```
<Clear summary of what changed>
```

Keep it simple. These get squashed anyway.

**Examples:**
```
Fix table review detection false positive
Add ground truth JSON file
Move import to module level
```

---

## Squash Merge Commits (Main Branch)

```
<Concise summary of what was accomplished> (Task reference if applicable)

<Context paragraph explaining what was added/changed and why>

Key changes:
- Bullet points for significant changes
- Important technical decisions

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Example:**
```
Complete clustering strategy for match boundary detection

Implemented temporal density clustering as an independent strategy for detecting match start
boundaries. Uses statistical density of team co-mentions in transcript to identify intro segments.
Complements venue-based detection for cross-validation.

Key changes:
- Clustering algorithm with configurable window size and density thresholds
- TDD test suite (7 new tests, 38/38 total passing)
- Side-by-side CLI comparison of venue vs clustering results
- 6/7 match detection rate (85.7%), 83% agreement with venue strategy

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```
