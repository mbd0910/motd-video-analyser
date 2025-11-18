# MOTD Analyser - Task Management System

This directory contains a structured, folder-based task management system for building the MOTD Analyser project.

## Quick Links

- **[BACKLOG.md](BACKLOG.md)** - Complete task inventory with status and time estimates
- **[task-workflow.md](../../.claude/commands/task-workflow.md)** - Workflow for implementing tasks

## Task Organization

All tasks are organized in a **folder-based structure** for consistency and clarity:

```
docs/tasks/
├── README.md                          # This file - explains the system
├── BACKLOG.md                         # Task inventory and status tracking
├── completed/                         # Archive of finished tasks
│   ├── 001-environment-setup/
│   │   └── README.md
│   ├── 002-create-project-structure/
│   │   └── README.md
│   ├── 011-analysis-pipeline/         # Phase 1 complete (running order detection)
│   │   ├── README.md
│   │   └── ... (9 task files)
│   └── ...
├── 012-classifier-integration/        # Current active task
│   ├── README.md                      # Task overview
│   └── 012-01-pipeline-integration.md # Pipeline integration + boundary detection
└── future/                            # Tentative tasks (YAGNI principle)
    ├── 012-validation-tools/
    ├── 013-refinement-tuning/
    ├── 014-batch-processing/
    └── 015-documentation/
```

## Task Types

### Standalone Tasks
Tasks that can be completed in a single implementation session.

**Structure:**
```
{number}-{name}/
└── README.md
```

**Example:** Task 013 (Refinement & Tuning)

### Epic Tasks
Larger tasks that are split into multiple discrete subtasks for easier execution.

**Structure:**
```
{number}-{name}/
├── README.md              # Epic overview
├── {number}a-{name}.md    # Subtask A
├── {number}b-{name}.md    # Subtask B
└── {number}c-{name}.md    # Subtask C
```

**Example:** Task 008 (Scene Detection Testing) has 3 subtasks:
- 008a: Create CLI command
- 008b: Test on video
- 008c: Validate and tune

## Workflow

### Using the Task Workflow Command

The recommended way to work on tasks is using the `/task-workflow` command:

```bash
/task-workflow 8    # Start task 008
/task-workflow      # Prompts for task number
```

This command will:
1. Read the task from `docs/tasks/{number}-*/README.md`
2. Check for subtasks and work through them sequentially
3. Guide you through planning, implementation, and code review
4. Handle checkboxes and validation checklists
5. Manage git branches and commits

See [`.claude/commands/task-workflow.md`](../../.claude/commands/task-workflow.md) for complete workflow details.

### Working with Epics

When you encounter an epic:

1. **Read the epic README.md** - Understand the overall objective
2. **Review subtasks** - Each subtask file (008a, 008b, etc.) has specific steps
3. **Work sequentially** - Complete subtasks in order (a → b → c)
4. **Update checkboxes** - Mark items complete in each subtask file as you go
5. **Validate each subtask** - Don't skip validation checklists

### Working with Standalone Tasks

For standalone tasks:

1. **Read the task README.md** - Single file contains all steps
2. **Follow the checklist** - Mark items complete as you progress
3. **Run validation** - Complete the validation checklist before finishing

## File Naming Conventions

### Task Folders
Format: `{number}-{kebab-case-name}/`

Examples:
- `008-scene-detection-testing/`
- `009-ocr-implementation/`
- `013-refinement-tuning/`

### Subtask Files
Format: `{number}{letter}-{kebab-case-name}.md`

Examples:
- `008a-create-cli-command.md`
- `008b-test-on-video.md`
- `009a-implement-ocr-reader.md`

## Checkbox Progress Tracking

All task and subtask files use checkboxes to track progress:

```markdown
## Validation Checklist
- [ ] CLI command works
- [x] Scenes JSON generated
- [ ] Key frames extracted
```

**Important:**
- Update checkboxes as you complete work
- Commit checkbox updates with code changes
- All checkboxes must be `[x]` before task completion

## Completed Tasks

Finished tasks are moved to `completed/` to keep the main task list clean:

```
completed/
├── 001-environment-setup/
├── 002-create-project-structure/
├── 003-007-*/                    # Core pipeline tasks
├── 011-analysis-pipeline/        # Running order detection (Phase 1)
└── ...
```

These are archived for reference but not actively worked on.

## Future Tasks

Tentative tasks are stored in `future/` following the YAGNI principle (You Aren't Gonna Need It). These tasks are created only when they're actually needed, not speculatively.

```
future/
├── 012-validation-tools/         # Original task 012 (moved when scope changed)
├── 013-refinement-tuning/        # Original task 013
├── 014-batch-processing/         # Original task 014
└── 015-documentation/            # Original task 015
```

Tasks in `future/` may be renamed, re-scoped, or discarded as the project evolves.

## Git Workflow Integration

### Branch Naming
```bash
git checkout -b feature/task-{number}-{slug}
```

Example: `feature/task-008-scene-detection-testing`

### Commit Frequency
- Commit after completing each subtask
- Commit after addressing each code review item
- Follow [COMMIT_STYLE.md](../../COMMIT_STYLE.md) conventions

### Squash Merge
After code review is complete:
1. Update `BACKLOG.md` status (⏳ → ✅)
2. Verify all checkboxes are marked `[x]`
3. Squash merge into main

See [task-workflow.md](../../.claude/commands/task-workflow.md) step 8 for details.

## Common Patterns

### Starting a New Task
```bash
# 1. Check backlog
open docs/tasks/BACKLOG.md

# 2. Use task-workflow command
/task-workflow 8

# 3. Or manually:
open docs/tasks/008-scene-detection-testing/README.md
git checkout -b feature/task-008-scene-detection-testing
```

### Splitting an Epic (If Not Already Split)
If you encounter an epic without subtasks:

1. Read the epic README.md
2. Identify discrete sub-tasks (3-6 recommended)
3. Create subtask files (008a, 008b, 008c)
4. Get user approval before implementation
5. Work through subtasks sequentially

### Tracking Progress
- **Individual progress**: Checkboxes in task/subtask files
- **Overall progress**: Status emojis in BACKLOG.md
- **Git history**: Commit messages and branch names

## Tips for Success

1. **Work sequentially** - Tasks build on each other
2. **Validate frequently** - Don't skip validation checklists
3. **Commit often** - Small, focused commits are better
4. **Ask for clarity** - If task requirements are unclear, ask before coding
5. **Reference completed tasks** - Look at tasks 001-007 for examples

## Questions?

- **What tasks exist?** → See [BACKLOG.md](BACKLOG.md)
- **How do I start a task?** → Use `/task-workflow {number}`
- **What's the git workflow?** → See [CLAUDE.md](../../CLAUDE.md#general-instructions-for-claude-code)
- **What's the commit style?** → See [COMMIT_STYLE.md](../../COMMIT_STYLE.md)
- **How do I work with epics?** → Read epic README.md, then work through subtasks (a → b → c)

---

**Ready to start?** Open [BACKLOG.md](BACKLOG.md) to see available tasks.
