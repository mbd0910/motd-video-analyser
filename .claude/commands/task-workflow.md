# Task Workflow Command

Workflow for implementing number task in docs/tasks folder: plan, execute, code review, merge.

## Usage

```bash
/task-workflow 15               # Combined mode: plan + execute in one session
/task-workflow                  # Prompts for task number
```

## Workflow Overview

**Combined Mode:** Task file creation → Implementation → Code Review (Implementation Iteration) → Squash Merge

---

## Instructions for Claude

1. **Get task number and verify folder**
   - If provided as argument, use it
   - If not provided, ask user: "Which task number should I work on?"
   - Verify folder exists: `docs/tasks/{number}-*/`
   - If not found, list available tasks from `docs/tasks/BACKLOG.md`
   - Read task from `docs/tasks/{number}-*/README.md`
   - Extract title and create slug (kebab-case, 3-4 meaningful words)

2. **Critical Thinking**
   - Plan by thinking hard
   - Critically assess the plan presented in the docs/tasks/{number}-*/README.md file
   - **Review domain documentation** if task involves business logic:
     * [Domain Glossary](../docs/domain/README.md) - Check for relevant terminology
     * [Business Rules](../docs/domain/business_rules.md) - Understand validation constraints
     * [Visual Patterns](../docs/domain/visual_patterns.md) - Review timing/structure if needed
   - Present task understanding to the user, and any suggested amendments to the plan based on your understanding of the codebase and the project.

2a. **Check if task has subtasks**
   - Look for subtask files in the task folder (e.g., `008a-*.md`, `008b-*.md`)
   - If subtasks exist: Work through them sequentially (a → b → c)
   - If no subtasks but task is marked as epic: Create subtask breakdown
   - Get user approval on subtask split before proceeding
   - Example: Task 008 → 3 subtasks (008a-create-cli, 008b-test, 008c-validate)

PAUSE HERE UNTIL USER IS HAPPY TO CONTINUE

3. **Create branch**
   - `git checkout -b feature/task-{number}-{slug}`

4. **Update Task Files**
   - If changes to the plan, aggressively edit task README.md to reflect new plan
   - For subtasks, update the specific subtask file you're working on
   - **Add Quick Context section** if missing (see [Sub-Task Template](references/subtask_template.md)):
     * Link to parent task, domain concepts, and business rules
     * Explain business value ("Why This Matters")
   - Use todo list style plan so items can be checked off one by one

PAUSE HERE UNTIL USER IS HAPPY TO CONTINUE

5. **Execute**
   - Work through todo list items one-by-one
   - Commit using COMMIT_STYLE.md after every todo list item is addressed
     * Todos should be reasonably scoped (feature/function level, not line-by-line)
     * Include checkbox update `[ ] → [x]` in the same commit as the code change
   - **Run validation checklist from task file before marking task complete**
   - If validation fails:
     * Present findings and suggest fix approach
     * Wait for user decision: fix now, defer, or adjust validation
   - If any clarifications are required, check with the user.

PAUSE HERE. SUGGEST USER EXECUTES CODE-REVIEW IN SEPARATE CLAUDE CODE SESSION

6. **Code Review Iteration**
   - Critically evaluate all code review feedback received
   - Be receptive to feedback, but don't blindly accept all feedback given

7. **Execute On Code Review Feedback**
   - Work through code review feedback items one-by-one
   - Commit using COMMIT_STYLE.md after every piece of feedback is addressed.

PAUSE HERE. SUGGEST USER ASKS CODE-REVIEWER TO DO A SECOND ROUND OF CODE REVIEW.
It's possible steps 6 and 7 will be conducted multiple times.

8. **Squash Merge** (Only after user confirms code review is complete)
   - Verify all checkboxes in task README.md and subtask files are marked `[x]`
   - Verify all commits follow COMMIT_STYLE.md
   - **Update `docs/tasks/BACKLOG.md` task status (⏳ → ✅) BEFORE merging**
   - **Move completed task to archive**: `git mv docs/tasks/{number}-{name}/ docs/tasks/completed/`
     * This keeps the active task list focused on remaining work
     * Preserves git history with git mv
   - **Ask user explicitly**: "Code review complete. Should I squash merge feature/task-{number}-{slug} into main?"
   - Only merge after explicit "yes"
   - Squash merge commit will include both the BACKLOG.md status update and the folder move

## Important Reminders

**Git Workflow (from CLAUDE.md):**
- Follow COMMIT_STYLE.md conventions
- Never merge without explicit user permission

**Task Dependencies:**
- Tasks build sequentially - don't skip ahead
- Each task assumes previous tasks are complete
- If starting mid-sequence, verify prerequisites are met

**Task File Updates:**
- Update checkboxes throughout execution: `- [ ]` → `- [x]`
- For epics with subtasks: Update checkboxes in individual subtask files
- Commit task file updates regularly
- All subtask files must be 100% complete before squash merge
- Upon completing a phase, always check checkboxes to ensure progress is accurately reflected in the task files