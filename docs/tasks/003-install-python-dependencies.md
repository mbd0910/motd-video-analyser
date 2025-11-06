# Task 003: Install Python Dependencies

## Objective
Create requirements.txt and install all Python dependencies.

## Prerequisites
- [002-create-project-structure.md](002-create-project-structure.md) completed
- Virtual environment activated

## Steps

### 1. Create requirements.txt
```bash
cat > requirements.txt << 'EOF'
# Core
opencv-python==4.8.1
numpy==1.24.3
pyyaml==6.0.1

# Scene Detection
scenedetect[opencv]==0.6.2

# OCR
easyocr==1.7.0
torch==2.1.0

# Transcription (using faster-whisper for 4x speed improvement)
faster-whisper==0.9.0

# Alternative: Standard whisper (uncomment if faster-whisper has issues)
# openai-whisper==20231117

# Testing
pytest==7.4.3
pytest-cov==4.1.0

# Utilities
python-dateutil==2.8.2
tqdm==4.66.1
EOF
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note**: This will take 5-10 minutes as it downloads PyTorch, EasyOCR models, etc.

### 3. Verify Installation
```bash
# Check key packages are installed
pip list | grep -E "(opencv|scenedetect|easyocr|faster-whisper|torch)"
```

Expected output should show:
- opencv-python
- scenedetect
- easyocr
- faster-whisper
- torch

### 4. Test Imports
```bash
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import easyocr; print('EasyOCR: OK')"
python -c "from faster_whisper import WhisperModel; print('faster-whisper: OK')"
python -c "from scenedetect import detect; print('scenedetect: OK')"
```

## Validation Checklist
- [ ] requirements.txt created
- [ ] All dependencies installed without errors
- [ ] All test imports work

## Estimated Time
10-15 minutes (mostly waiting for downloads)

## Troubleshooting

### If torch installation fails on M3 Mac:
```bash
pip install torch==2.1.0 torchvision torchaudio
```

### If EasyOCR has issues:
EasyOCR will download additional model files (~100MB) on first use. This is normal.

### If faster-whisper has issues:
Fall back to standard whisper:
```bash
pip uninstall faster-whisper
pip install openai-whisper==20231117
```
(You'll need to update code later to use `import whisper` instead)

## Notes
- Using `faster-whisper` instead of standard `openai-whisper` for 4x speed improvement
- PyTorch installation includes GPU support for M3 Pro
- EasyOCR models will be downloaded automatically on first run

## Next Task
[004-create-team-names-file.md](004-create-team-names-file.md)
