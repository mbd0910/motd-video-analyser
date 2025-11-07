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

1. **Get task number and verify file**
   - If provided as argument, use it
   - If not provided, ask user: "Which task number should I work on?"
   - Verify file exists: `docs/tasks/{number}-*.md`
   - If not found, list available tasks from `docs/tasks/README.md`
   - Extract title and create slug (kebab-case, 3-4 meaningful words)

2. **Critical Thinking**
   - Plan by thinking hard
   - Critically assess the plan presented in the docs/tasks/{tasknumber}-description.md file
   - Present task understanding to the user, and any suggested amendments to the plan based on your understanding of the codebase and the project.

2a. **Check if task is an epic (008-015)**
   - Epics combine multiple sub-tasks and MUST be split before implementation
   - If epic: Create sub-task breakdown in the task file
   - Get user approval on sub-task split before proceeding
   - Example: Task 009 (OCR Epic) → 5 discrete sub-tasks (OCR reader, team matcher, CLI, test run, validation)

PAUSE HERE UNTIL USER IS HAPPY TO CONTINUE

3. **Create branch**
   - `git checkout -b feature/task-{number}-{slug}`

4. **Update Task Markdown File**
   - If changes to the plan, aggressively edit task markdown file to reflect new plan.
   - Use todo list style plan so items can be checked off one by one.

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
   - Verify all checkboxes in task file are marked `[x]`
   - Verify all commits follow COMMIT_STYLE.md
   - **Update `docs/tasks/README.md` task status (⏳ → ✅) BEFORE merging**
   - **Ask user explicitly**: "Code review complete. Should I squash merge feature/task-{number}-{slug} into main?"
   - Only merge after explicit "yes"
   - Squash merge commit will include the README.md status update

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
- Commit task file updates regularly
- Task file must be 100% complete before squash merge
- Upon completing a phase, always check checkboxes to ensure progress is accurately reflected in the task markdown file.