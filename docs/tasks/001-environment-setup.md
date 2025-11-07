# Task 001: Environment Setup

## Objective
Set up Python virtual environment and prepare for project development.

## Prerequisites
- Python 3.12.7 installed (via asdf or other version manager)
- ffmpeg installed (✓ already done)

## Steps

### 1. Set Python Version
```bash
cd /Users/michael/code/motd-video-analyser
asdf local python 3.12.7
# or use your preferred version manager
```

### 2. Create Virtual Environment
```bash
python -m venv venv
```

### 3. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 4. Upgrade pip
```bash
pip install --upgrade pip
```

### 5. Verify Setup
```bash
# Verify Python version
python --version
# Should output: Python 3.12.7

# Verify ffmpeg is installed
ffmpeg -version
# Should show ffmpeg version info
```

## Validation Checklist
- [x] Virtual environment created successfully
- [x] Virtual environment activated (you should see `(venv)` in your prompt)
- [x] pip upgraded to latest version
- [x] `python --version` shows 3.12.7
- [x] `ffmpeg -version` works

## Estimated Time
5-10 minutes

## Notes
- Keep the virtual environment activated for all subsequent tasks
- If you need to deactivate: `deactivate`
- To reactivate later: `source venv/bin/activate`

## Next Task
[002-create-project-structure.md](002-create-project-structure.md)
