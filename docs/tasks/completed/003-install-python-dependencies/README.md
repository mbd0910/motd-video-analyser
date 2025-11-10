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
opencv-python==4.12.0.88
numpy>=2.0.0,<2.4.0
pyyaml==6.0.3

# Scene Detection
scenedetect[opencv]==0.6.7.1

# OCR
easyocr==1.7.2
torch==2.9.0
torchvision==0.20.0
torchaudio==2.9.0

# Transcription (using faster-whisper for 4x speed improvement)
faster-whisper==1.1.0
requests>=2.32.0  # Required by faster-whisper

# Testing
pytest==8.4.2
pytest-cov==7.0.0

# Utilities
python-dateutil==2.9.0.post0
tqdm==4.67.1
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
- [x] requirements.txt created
- [x] All dependencies installed without errors
- [x] All test imports work
- [x] PyTorch MPS backend available and working on M3 Mac

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
