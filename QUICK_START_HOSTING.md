# 🎯 Quick Start - Essential Files Only

If you're in a hurry, here are the **ABSOLUTE MINIMUM** files you need:

## 📦 Minimum Required Files

```
Pdf_Video_Generation/
│
├── run_backend.py              # ⭐ Entry point
├── requirements.txt            # ⭐ Dependencies
├── .env                        # ⭐ API keys (create this)
│
├── app/
│   ├── __init__.py
│   ├── config.py               # ⭐ Configuration
│   ├── logging_config.py       # ⭐ Logging
│   │
│   ├── api/                    # ⭐ FastAPI Backend
│   │   ├── __init__.py
│   │   ├── main.py             # ⭐⭐⭐ Main API app
│   │   ├── job_service.py      # ⭐ Job tracking
│   │   ├── pipeline_service.py # ⭐⭐⭐ Core pipeline
│   │   └── cartesia_service.py # Cartesia TTS
│   │
│   ├── phase1_pdf_processing/  # ⭐ PDF Processing
│   │   ├── __init__.py
│   │   ├── service.py          # ⭐ PDF extraction
│   │   ├── processor.py        # PDF logic
│   │   ├── image_extractor.py  # Extract images
│   │   ├── text_cleaner.py     # ⭐ Clean text
│   │   └── utils/
│   │       └── pdf_extraction_strategies.py
│   │
│   ├── phase2_ai_services/     # ⭐ AI Services
│   │   ├── __init__.py
│   │   ├── openai_client.py    # ⭐⭐ OpenAI TTS
│   │   ├── cartesia_client.py  # Cartesia TTS
│   │   ├── book_summary.py     # Summary generation
│   │   └── pdf_summarizer.py   # PDF summarizer
│   │
│   ├── phase3_audio_processing/ # ⭐ Audio
│   │   ├── __init__.py
│   │   └── mastering.py        # ⭐ Audio mastering
│   │
│   └── phase4_video_generation/ # ⭐ Video
│       ├── __init__.py
│       └── renderer.py         # ⭐⭐ Video rendering
│
└── assets/                     # ⭐ Static files
    ├── fonts/
    │   └── Book Antiqua.ttf    # ⭐ Font file
    └── backgrounds/
        ├── 1920x1080-white-solid-color-background.jpg  # ⭐
        ├── 854x480-white-background.jpg                # ⭐
        └── white-paper-texture-background.jpg          # ⭐
```

## ⚡ Super Quick Deployment (5 minutes)

### 1️⃣ Upload to Server
```bash
# Upload these directories:
- Pdf_Video_Generation/app/
- Pdf_Video_Generation/assets/
- Pdf_Video_Generation/run_backend.py
- Pdf_Video_Generation/requirements.txt
```

### 2️⃣ Install Dependencies
```bash
cd Pdf_Video_Generation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Create .env File
```bash
nano .env
```

Paste this (replace with your OpenAI key):
```env
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
VIDEO_FPS=30
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
```

### 4️⃣ Run It!
```bash
python run_backend.py
```

Done! Backend running on `http://0.0.0.0:8000`

---

## 🧪 Test It (1 minute)

### Test health:
```bash
curl http://localhost:8000/health
```

### Upload PDF:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@your_file.pdf" \
  -F "start_page=1" \
  -F "end_page=2"
```

### Check status:
```bash
curl http://localhost:8000/api/jobs/{job_id}
```

---

## 🔥 What Each File Does

| File | What It Does | Can Skip? |
|------|-------------|-----------|
| `app/api/main.py` | Main FastAPI app with all endpoints | ❌ NO |
| `app/api/pipeline_service.py` | Orchestrates entire pipeline | ❌ NO |
| `app/api/job_service.py` | Tracks job status | ❌ NO |
| `app/phase1_pdf_processing/service.py` | Extracts text from PDF | ❌ NO |
| `app/phase1_pdf_processing/text_cleaner.py` | Cleans text for narration | ❌ NO |
| `app/phase2_ai_services/openai_client.py` | Generates audio + timestamps | ❌ NO |
| `app/phase3_audio_processing/mastering.py` | Enhances audio quality | ❌ NO |
| `app/phase4_video_generation/renderer.py` | Creates video frames | ❌ NO |
| `app/config.py` | Loads settings & API keys | ❌ NO |
| `assets/fonts/Book Antiqua.ttf` | Font for video text | ❌ NO |
| `assets/backgrounds/*.jpg` | Background images | ❌ NO |
| `app/api/cartesia_service.py` | Cartesia TTS (alternative) | ✅ YES (if using OpenAI only) |
| `app/phase2_ai_services/cartesia_client.py` | Cartesia TTS client | ✅ YES (if using OpenAI only) |
| `app/phase2_ai_services/book_summary.py` | Book summary generation | ✅ YES (if no summaries) |
| `frontend/` | React frontend | ✅ YES (if backend only) |
| `scripts/` | Testing scripts | ✅ YES |

---

## 💡 How Data Flows

```
USER
  ↓
POST /api/upload (PDF file)
  ↓
FastAPI (app/api/main.py)
  ↓
PipelineService (app/api/pipeline_service.py)
  ↓
┌─────────────────────────────────────┐
│ Phase 1: PDF Processing             │
│ - Extract text (service.py)         │
│ - Clean text (text_cleaner.py)      │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ Phase 2: AI Services                │
│ - Generate audio (openai_client.py) │
│ - Create timestamps (Whisper)       │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ Phase 3: Audio Processing           │
│ - Master audio (mastering.py)       │
│ - Regenerate timestamps (Whisper)   │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ Phase 4: Video Generation           │
│ - Generate frames (renderer.py)     │
│ - Combine with audio (FFmpeg)       │
└─────────────────────────────────────┘
  ↓
FINAL VIDEO (saved to jobs/{job_id}/)
  ↓
USER downloads via GET /api/jobs/{job_id}/download/video
```

---

## 🎯 Most Important Files (Top 10)

1. **`app/api/main.py`** - All API endpoints
2. **`app/api/pipeline_service.py`** - Core orchestration
3. **`app/phase4_video_generation/renderer.py`** - Video generation
4. **`app/phase2_ai_services/openai_client.py`** - Audio generation
5. **`app/phase1_pdf_processing/service.py`** - PDF extraction
6. **`app/phase1_pdf_processing/text_cleaner.py`** - Text cleaning
7. **`app/phase3_audio_processing/mastering.py`** - Audio enhancement
8. **`app/config.py`** - Configuration
9. **`run_backend.py`** - Entry point
10. **`.env`** - API keys

---

## 🚨 Common Mistakes

❌ **Forgot to create `.env` file**
```bash
# Fix:
nano .env
# Add: OPENAI_API_KEY=sk-proj-...
```

❌ **Missing fonts/backgrounds**
```bash
# Fix:
scp -r assets/ user@server:/path/to/Pdf_Video_Generation/
```

❌ **FFmpeg not installed**
```bash
# Fix:
sudo apt install ffmpeg -y
```

❌ **Wrong Python version**
```bash
# Fix:
python3 --version  # Must be 3.10+
```

❌ **Virtual environment not activated**
```bash
# Fix:
source venv/bin/activate
```

---

## 📝 Summary

**Bare minimum to host:**
1. Upload `app/` directory
2. Upload `assets/` directory
3. Upload `run_backend.py` and `requirements.txt`
4. Create `.env` with OpenAI API key
5. Install dependencies: `pip install -r requirements.txt`
6. Run: `python run_backend.py`

**That's it! 🎉**

For detailed explanations, see `HOSTING_GUIDE.md`
