# Commit Message Style

## Overview

This repository uses **different commit message styles** depending on the branch:

- **Feature branch commits**: Conventional commit format for structured development
- **Main branch commits** (squash merges): Human-readable summaries for project history

---

## Feature Branch Commits

**When working on feature branches**, use conventional commit prefixes for clarity:

### Format
```
<type>(<scope>): <short summary>

[Optional body with detailed context]
```

### Types
- `feat`: New feature or enhancement
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `chore`: Build, config, or tooling changes

### Examples
```
feat(clustering): Implement temporal density clustering strategy

Added _find_team_mentions(), _find_co_mention_windows(), and _identify_densest_cluster()
methods to detect match boundaries using team co-mention density in transcript.
```

```
fix(venue): Use partial_ratio for substring matching in venue detection

Prevents false negatives when venue name appears within longer phrases.
```

---

## Squash Merge Commits (Main Branch)

**When squash merging to main**, use human-readable summaries **without conventional prefixes**:

### Format
```
[Concise summary of what was accomplished] ([Task reference if applicable])

[Context paragraph explaining what was added/changed and why]

Key additions/changes:
- Bullet points for significant new components/features
- New dependencies with brief explanation of why
- Important technical decisions or constraints

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Example
```
Complete clustering strategy for match boundary detection (Task 012-01)

Implemented temporal density clustering as an independent strategy for detecting match start
boundaries. Uses statistical density of team co-mentions in transcript to identify intro segments.
Complements venue-based detection for cross-validation.

Key additions:
- Clustering algorithm with configurable window size and density thresholds
- TDD test suite (7 new tests, 38/38 total passing)
- Side-by-side CLI comparison of venue vs clustering results
- Debug mode with comprehensive clustering diagnostics
- 6/7 match detection rate (85.7%), 83% agreement with venue strategy

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Why This Approach?

**Feature branches**: Conventional commits provide structure during iterative development
- Clear categorization (feat/fix/docs/test)
- Easy to scan during code review
- Consistent format across contributors

**Main branch**: Human-readable summaries provide project narrative
- No technical jargon for stakeholders
- Focus on business value and outcomes
- Clean, professional commit history