# Task 002: Create Project Structure

## Objective
Create the directory structure and skeleton files for the project.

## Prerequisites
- [001-environment-setup.md](001-environment-setup.md) completed
- Virtual environment activated

## Steps

### 1. Create Source Directory Structure
```bash
mkdir -p src/motd_analyzer/scene_detection
mkdir -p src/motd_analyzer/ocr
mkdir -p src/motd_analyzer/transcription
mkdir -p src/motd_analyzer/analysis
mkdir -p src/motd_analyzer/validation
mkdir -p src/motd_analyzer/pipeline
mkdir -p src/motd_analyzer/utils
```

### 2. Create Data Directories
```bash
mkdir -p data/teams
mkdir -p data/videos
mkdir -p data/cache
mkdir -p data/output
```

### 3. Create Config and Supporting Directories
```bash
mkdir -p config
mkdir -p tests
mkdir -p logs
```

### 4. Create Python Package Files
```bash
touch src/motd_analyzer/__init__.py
touch src/motd_analyzer/__main__.py
touch src/motd_analyzer/scene_detection/__init__.py
touch src/motd_analyzer/ocr/__init__.py
touch src/motd_analyzer/transcription/__init__.py
touch src/motd_analyzer/analysis/__init__.py
touch src/motd_analyzer/validation/__init__.py
touch src/motd_analyzer/pipeline/__init__.py
touch src/motd_analyzer/utils/__init__.py
```

### 5. Create .gitignore
```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Data
data/videos/
data/cache/
data/output/

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Model files
*.pt
*.pth
*.onnx
EOF
```

## Validation Checklist
- [ ] All source directories created
- [ ] All data directories created
- [ ] Config, tests, logs directories created
- [ ] All `__init__.py` files created
- [ ] `.gitignore` created

### Verify with:
```bash
tree -L 3 src/
tree -L 2 data/
ls -la | grep gitignore
```

## Estimated Time
5 minutes

## Notes
- `data/videos/`, `data/cache/`, and `data/output/` will be gitignored as they'll contain large files
- The `__init__.py` files make Python treat the directories as packages

## Next Task
[003-install-python-dependencies.md](003-install-python-dependencies.md)
