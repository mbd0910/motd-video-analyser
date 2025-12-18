# Issue Workflow Command

> **Last reviewed:** 2025-12-18

Complete workflow for implementing GitHub issues with critical thinking, planning, execution, and code review.

## Usage

```bash
/issue-workflow 15              # Plan + execute issue #15
/issue-workflow                 # Prompts for issue number
```

## Workflow Overview

Critical Thinking ‖ Branch → Task file → Implementation ‖ Code Review ‖ Merge

---

## Code Quality Standards

Before implementing any feature, familiarise yourself with our coding standards:

**Reference Files:**
- [Code Quality Checklist](.claude/commands/references/code_quality_checklist.md)
- [Python Guidelines](.claude/commands/references/python_guidelines.md)
- [Architecture Patterns](.claude/commands/references/python_architecture_patterns.md)
- [ML/Pipeline Patterns](.claude/commands/references/ml_pipeline_patterns.md)
- [Testing Guidelines](.claude/commands/references/testing_guidelines.md)

**Domain Documentation:**
- [Domain Glossary](docs/domain/README.md) - Terminology (FT Graphics, Running Order, etc.)
- [Business Rules](docs/domain/business_rules.md) - Validation logic, accuracy requirements
- [Visual Patterns](docs/domain/visual_patterns.md) - Episode structure, timing patterns

See [references/README.md](.claude/commands/references/README.md) for overview.

---

## Instructions for Claude

### Phase 1: Critical Thinking

**Think hard about the requirements before creating any plan:**

1. **Critically assess the issue**
   - What problem are we really solving?
   - What edge cases or gotchas might be hidden?
   - What assumptions is the issue making - are they valid?
   - Is there a simpler approach?
   - Check guidelines: What code smells should we avoid?

2. **Challenge the approach**
   - If the issue includes an implementation plan, is it the best approach?
   - Are there technical debt opportunities we should take?
   - What could go wrong with this design?
   - Which components need tests? (See testing_guidelines.md)

3. **Present your thinking to the user**
   - Explain your understanding of the problem
   - Propose amendments or improvements to the plan
   - Document key decisions and assumptions
   - Get alignment before proceeding

**PAUSE** - Get user alignment before proceeding.

### Phase 2: Setup

1. **Get issue number**
   - If provided as argument, use it
   - If not provided, ask user: "Which issue number should I work on?"
   - Fetch issue details: `gh issue view {number}`
   - Extract title and create slug (kebab-case, max 3-4 words)

2. **Create feature branch**
   - `git checkout -b feature/issue-{number}-{slug}`
   - **DO NOT commit directly to main branch**

3. **Create task folder and file**
   - Create folder: `docs/tasks/issue-{number-padded}/` (e.g., `issue-007/`)
   - Create file: `docs/tasks/issue-{number-padded}/issue-{number-padded}.md` (e.g., `issue-007/issue-007.md`)
   - Generate structure tailored to issue complexity (don't copy from templates)
   - **Required sections:**
     - Link to GitHub issue at top
     - Overview (scope summary, key deliverable)
     - Critical Thinking Phase (document key decisions, challenge assumptions, consider alternatives)
     - Phase 0: Setup (branch creation, initial commit)
     - Phase 1-N: Implementation phases (use checkboxes `- [ ]` for trackable tasks)
     - Final Phase: Testing, Code Review, Documentation, Merge (reference this workflow)
     - Notes & Decisions section at bottom (for architectural decisions only - not code review minutiae)
   - **Section format rules:**
     - Implementation phases: Use checkboxes for concrete tasks
     - Testing/Review/Merge: Reference standard workflow rather than duplicating steps
     - Critical thinking: Explain WHY decisions were made, not just WHAT was decided
   - **Reference existing task files** as examples, but tailor structure to your specific issue
   - **Do not copy-paste** from other task files - generate fresh structure based on requirements

4. **Initial commit**
   - Commit message: `"Add task tracking file for issue #{number}"`
   - Commit style: Follow COMMIT_STYLE.md conventions

5. **Establish bi-directional link**
   - Task file already links to issue (in file header)
   - Add comment to GitHub issue:
     ```bash
     gh issue comment {number} -b "📋 Task tracking: [docs/tasks/issue-{number-padded}/issue-{number-padded}.md](https://github.com/mbd0910/motd-video-analyser/blob/main/docs/tasks/issue-{number-padded}/issue-{number-padded}.md)"
     ```

---

### Phase 3: Implementation

6. **Work through implementation phases**
   - Follow the phased TODO structure in task file
   - Work through todo items one by one
   - **After completing each todo item (or small group of related items):**
     - Commit using COMMIT_STYLE.md format (refs #{number})
     - **Include checkbox update (`[ ]` → `[x]`) in the same commit**
   - **Why atomic commits?** Task file is a historical record - it should move with the code

**PAUSE** - Implementation complete. Moving to code review.

---

### Phase 4: Code Review

7. **Run code review**
    - Say: "Implementation phases complete."
    - **Recommend:** "For fresh perspective, consider running `/code-review main` in a separate Claude Code session"
    - Execute: `/code-review main` (or appropriate base branch)

**PAUSE** - Code review complete. Time to evaluate feedback.

8. **Critically evaluate code review feedback**
    - Present code review findings to user
    - **Important:** Be receptive to feedback, but don't blindly accept all suggestions
    - Consider each item:
      - Does it improve code quality?
      - Does it align with project patterns?
      - Is it worth the effort?
    - Ask user: "Which code review items should we address?"

9. **Execute on feedback**
    - Implement selected feedback items
    - Each feedback item = one commit (refs #{number})

**PAUSE** - Check if second round of review needed.

10. **Consider second code review round**
    - After addressing feedback, significant changes may need re-review
    - Ask user: "Should we do a second round of code review? (yes/no)"
    - If yes, return to step 7

---

### Phase 5: Merge

**PAUSE** - Ready to squash merge? Verify everything first.

11. **Verify task file completion**
    - Read `docs/tasks/issue-{number-padded}/issue-{number-padded}.md`
    - Count checkboxes: `- [ ]` (incomplete) vs `- [x]` (complete)
    - **If ANY incomplete:** Show list and **STOP** - do not proceed to merge
    - **If ALL complete:** Confirm "✓ All task file items complete ({count}/{count})"

12. **Verify commit quality**
    - Review commits: `git log main..HEAD --oneline`
    - Check commits follow COMMIT_STYLE.md conventions
    - Confirm: "✓ All commits follow COMMIT_STYLE.md"

13. **Ask for squash merge approval**
    - Display verification results
    - Ask: "Should I squash merge feature/issue-{number}-{slug} into main? (yes/no)"
    - **Only proceed if user says "yes"**

14. **Execute squash merge (only if approved)**
    - Create squash merge commit (COMMIT_STYLE.md format)
    - Include "resolves #{number}" to auto-close issue
    - Push to main
    - Remind user: Issue will auto-close, feature branch will be deleted
    - Task file remains at docs/tasks/issue-{number-padded}/ for reference

---

## Important Reminders

**Critical Thinking First:**
- Always challenge the plan before implementing
- Propose amendments based on your codebase knowledge
- Get user alignment before proceeding

**Always Use Feature Branches:**
- Never commit directly to main
- Create feature branch immediately after getting issue number

**Atomic Commits:**
- One todo item = one commit
- Include code changes + checkbox update in the same commit
- Why? Task file is historical record - it should move with the code

**Code Review Philosophy:**
- Recommend separate Claude Code session for fresh perspective
- Critically evaluate feedback - don't blindly accept all suggestions

**Task Files:**
- Focus on implementation plan, not changelog
- Notes & Decisions section is for architectural decisions only
- Don't document code review minutiae - the code is its own documentation

**Never Skip:**
- Critical thinking and plan challenge phase
- Task file completion verification (ALL checkboxes must be complete)
- User approval before squash merge

---

## Notes

- All issues use folder structure: `docs/tasks/issue-{number-padded}/`
- Integrates with existing `/code-review` command
- Maintains full traceability: task file ↔ issue ↔ branch ↔ commits
- Task files remain in docs/tasks/ for reference
