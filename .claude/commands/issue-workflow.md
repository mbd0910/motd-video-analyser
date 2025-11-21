# Issue Workflow Command

Complete workflow for implementing GitHub issues with critical thinking, planning, execution, and code review.

## Usage

```bash
/issue-workflow 15              # Combined mode: plan + execute in one session
/issue-workflow 15 --plan-only  # Create task file and links, stop before implementation
/issue-workflow 15 --execute    # Execute existing task file (assumes planning done)
/issue-workflow                 # Prompts for issue number
```

## Workflow Overview

**Combined Mode:** Critical Thinking → Task file creation → Implementation → Code Review
**Plan-Only Mode:** Critical Thinking → Task file creation → Stop
**Execute Mode:** Implementation → Code Review (reads existing task file)

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

### Phase -1: Critical Thinking (All Modes)

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

**PAUSE HERE UNTIL USER IS HAPPY TO CONTINUE**

### Phase 0: Setup (All Modes)

1. **Get issue number**
   - If provided as argument, use it
   - If not provided, ask user: "Which issue number should I work on?"
   - Fetch issue details: `gh issue view {number}`
   - Extract title and create slug (kebab-case, max 3-4 words)

2. **Determine mode**
   - Check for `--plan-only` flag → Planning mode
   - Check for `--execute` flag → Execution mode
   - No flags → Combined mode (default)

### Planning Mode Steps (`--plan-only` or combined mode)

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
     - Notes & Decisions section at bottom (capture learnings, deviations, architecture decisions)
   - **Section format rules:**
     - Implementation phases: Use checkboxes for concrete tasks
     - Testing/Review/Merge: Reference standard workflow (see below) rather than duplicating steps
     - Critical thinking: Explain WHY decisions were made, not just WHAT was decided
   - **Reference existing task files** as examples, but tailor structure to your specific issue
   - **Do not copy-paste** from other task files - generate fresh structure based on requirements

4. **Create branch**
   - Planning mode: `git checkout -b plan/issue-{number}`
   - Combined/Execute mode: `git checkout -b feature/issue-{number}-{slug}`

5. **Initial commit**
   - Commit message: `"Add task tracking file for issue #{number}"`
   - Commit style: Follow COMMIT_STYLE.md conventions

6. **Branch handling**
   - **If `--plan-only` mode:**
     - Ask user: "Planning complete. Ready to squash merge plan branch to main? (yes/no)"
     - If yes: Create squash merge commit following COMMIT_STYLE.md
     - After successful merge, establish bi-directional link (step 7)
     - Stop here
   - **If combined mode:**
     - Establish bi-directional link (step 7)
     - Remind user: "Task file created. Ready to start implementation."
     - Continue to Execution Phase

7. **Establish bi-directional link**
   - Task file already links to issue (in file header)
   - Add comment to GitHub issue:
     ```bash
     gh issue comment {number} -b "📋 Task tracking: [docs/tasks/issue-{number-padded}/issue-{number-padded}.md](https://github.com/mbd0910/motd-video-analyser/blob/main/docs/tasks/issue-{number-padded}/issue-{number-padded}.md)"
     ```
   - Note: This happens after commit (or after merge in plan-only mode) so the link is immediately clickable

---

### Execution Phase (`--execute` or combined mode)

8. **Load task file (execute mode only)**
   - Read `docs/tasks/issue-{number-padded}/issue-{number-padded}.md` from main branch
   - Verify it exists and has bi-directional link
   - Create feature branch: `git checkout -b feature/issue-{number}-{slug}`

9. **Work through implementation phases**
   - Follow the phased TODO structure in task file
   - Work through todo items one by one
   - **After completing each todo item (or small group of related items):**
     - Commit using COMMIT_STYLE.md format (refs #{number})
     - **Include checkbox update (`[ ]` → `[x]`) in the same commit**
     - Include any relevant "Notes & Decisions" updates in the same commit
   - **Why atomic commits?** Task file is a historical record - it should move with the code
   - **Benefit:** If you revert a code commit, the checkbox automatically reverts too (stays consistent)

---

**PAUSE HERE - Implementation complete. Time for code review.**

10. **Suggest code review in separate session**
    - Say: "Implementation phases complete."
    - **Recommend:** "For fresh perspective, consider running `/code-review main` in a separate Claude Code session"
    - Ask: "Ready for code review? (yes/no/not yet)"
    - If "not yet", stop and wait for user

11. **Run code review (if user approved and same session)**
    - Execute: `/code-review main` (or appropriate base branch)
    - Wait for code review results
    - Note: Separate session provides more objective review

---

**PAUSE HERE - Code review complete. Time to evaluate feedback.**

12. **Critically evaluate code review feedback**
    - Present code review findings to user
    - **Important:** Be receptive to feedback, but don't blindly accept all suggestions
    - Consider each item:
      - Does it improve code quality?
      - Does it align with project patterns?
      - Is it worth the effort?
    - Ask user: "Which code review items should we address?"

13. **Execute on feedback**
    - Implement selected feedback items one by one
    - Each feedback item = one commit (refs #{number})
    - Include checkbox/notes updates in same commit
    - Document what was addressed in task file

**PAUSE HERE - Check if second round of review needed.**

14. **Consider second code review round**
    - After addressing feedback, significant changes may need re-review
    - Ask user: "Should we do a second round of code review? (yes/no/done)"
    - If yes, return to step 10
    - If done, document which items were addressed/skipped and continue

---

**PAUSE HERE - Ready to squash merge? Let's verify everything first.**

15. **Verify task file completion**
    - Read `docs/tasks/issue-{number-padded}/issue-{number-padded}.md`
    - Count checkboxes: `- [ ]` (incomplete) vs `- [x]` (complete)
    - **Note:** Only count implementation phase checkboxes (Code Review phase uses narrative format)

    **If ANY incomplete checkboxes found:**
    - Show list: "⚠️ Task file has {count} incomplete items:"
    - **STOP** - Do not proceed to merge
    - Wait for user to complete or explain

    **If ALL checkboxes complete:**
    - Confirm: "✓ All task file items complete ({count}/{count})"
    - Proceed to next check

16. **Verify commit quality**
    - Review commits: `git log main..HEAD --oneline`
    - Check commits follow COMMIT_STYLE.md conventions
    - Check task file is committed and up-to-date
    - Confirm: "✓ All commits follow COMMIT_STYLE.md"

17. **Ask for squash merge approval**
    - Display: "✓ All task file items complete ({count}/{count})"
    - Display: "✓ All commits follow COMMIT_STYLE.md"
    - Say: "Ready to squash merge to main."
    - Ask: "Should I squash merge feature/issue-{number}-{slug} into main? (yes/no)"
    - **Only proceed if user says "yes"**

18. **Execute squash merge (only if approved)**
    - Create squash merge commit (COMMIT_STYLE.md format)
    - Include "resolves #{number}" to auto-close issue
    - Push to main
    - Remind user:
      - Issue will auto-close via "resolves #{number}"
      - Feature branch will be deleted automatically
    - Task file remains at docs/tasks/issue-{number-padded}/ for reference

---

## Important Reminders

**Critical Thinking First:**
- Always challenge the plan before implementing
- Propose amendments based on your codebase knowledge
- PAUSE for user alignment before proceeding

**Atomic Commits:**
- One todo item = one commit
- Include code changes + checkbox update + notes in the same commit
- Why? Task file is historical record - should move with code
- Benefit: Reverts stay consistent (revert code = revert checkbox automatically)

**Code Review Philosophy:**
- Recommend separate Claude Code session for fresh perspective
- Critically evaluate feedback - don't blindly accept all suggestions
- Consider second round of review after significant changes

**Four Pause Points:**
1. After critical thinking - Get alignment on approach
2. After implementation - Before code review
3. After code review - Evaluate feedback critically
4. Before squash merge - Verify completion

**Never Skip:**
- Critical thinking and plan challenge phase
- Task file completion verification (ALL checkboxes must be complete)
- Commit quality verification (must follow COMMIT_STYLE.md)
- User approval at each pause point

**Task File Format - Code Review Phase:**
Use narrative/instruction format instead of checkboxes (see existing task files for example format).

---

## Notes

- All issues use folder structure: `docs/tasks/issue-{number-padded}/`
- Integrates with existing `/code-review` command
- Supports both single-session and multi-session workflows
- Critical quality gates prevent premature merging:
  - ALL task file checkboxes must be complete
  - ALL commits must follow COMMIT_STYLE.md
  - Explicit user approval required
- Maintains full traceability: task file ↔ issue ↔ branch ↔ commits
- Task files remain in docs/tasks/ for reference (not moved to completed/)
