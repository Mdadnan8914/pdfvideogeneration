# 🚀 PDF to Video Generation - Complete Hosting Guide

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [How It Works](#how-it-works)
3. [Essential Files for Hosting](#essential-files-for-hosting)
4. [Architecture & Flow](#architecture--flow)
5. [Deployment Steps](#deployment-steps)
6. [Environment Configuration](#environment-configuration)

---

## 📖 Project Overview

**What This Project Does:**
- Converts PDF books/documents into narrated video content
- Uses AI (OpenAI/Cartesia) for text-to-speech generation
- Automatically generates timestamps and syncs text with audio
- Creates professional videos with customizable backgrounds and fonts
- Supports multiple video formats (1080p, 480p, reels/shorts)

**Tech Stack:**
- **Backend Framework**: FastAPI (Python)
- **AI Services**: OpenAI (GPT-4o-mini, Whisper, TTS), Cartesia TTS
- **Video Processing**: MoviePy, ImageIO-ffmpeg
- **PDF Processing**: PyMuPDF, pdfplumber, pdfminer.six
- **Audio Processing**: Custom mastering pipeline
- **Frontend**: React (separate directory)

---

## 🔍 How It Works

### **Complete Pipeline Flow:**

```
1. PDF UPLOAD (via API)
   ↓
2. PDF PROCESSING (Phase 1)
   - Extract text from PDF pages
   - Detect book type (novel/textbook/etc.)
   - Extract tables and images
   - Filter pages based on user input (start_page to end_page)
   ↓
3. TEXT CLEANING (Phase 1.5)
   - Remove unwanted characters
   - Clean formatting
   - Prepare narration-ready script
   ↓
4. AI SERVICES (Phase 2)
   - Detect book genre (fiction, non-fiction, etc.)
   - Generate audio narration (OpenAI TTS or Cartesia)
   - Create word-level timestamps using Whisper
   ↓
5. AUDIO MASTERING (Phase 3)
   - Apply audio effects (compression, EQ, normalization)
   - Enhance audio quality for professional output
   - Regenerate timestamps from processed audio (for perfect sync)
   ↓
6. VIDEO RENDERING (Phase 4)
   - Generate video frames with synchronized text
   - Highlight words as they're spoken
   - Combine with audio to create final MP4
   ↓
7. OPTIONAL: SUMMARY GENERATION
   - Extract full book text
   - Generate 10k+ word summary using GPT-4o-mini
   - Can create separate summary video
```

### **Key Features:**

1. **Multiple Video Types:**
   - **Main Video**: Selected page range from PDF
   - **Summary Video**: AI-generated book summary (~1 hour)
   - **Reels/Shorts**: Social media optimized (9:16 aspect ratio)

2. **Voice Providers:**
   - **OpenAI**: High-quality TTS with "onyx" voice
   - **Cartesia**: Advanced TTS with customizable voices/models

3. **Smart Timestamp Sync:**
   - Initial timestamps from voice provider
   - **Re-generation from processed audio** ensures perfect video-audio sync
   - Word-level precision for text highlighting

---

## 📁 Essential Files for Hosting

### **🔴 CRITICAL - Must Have:**

#### 1. **Backend Entry Point**
- `run_backend.py` - Starts the FastAPI server
- `app/api/main.py` - Main API application with all endpoints

#### 2. **Core Services**
- `app/api/pipeline_service.py` - Orchestrates entire video generation
- `app/api/job_service.py` - Manages job status/tracking
- `app/api/cartesia_service.py` - Cartesia TTS integration

#### 3. **Phase Processing**
```
app/phase1_pdf_processing/
  ├── service.py              # PDF text extraction
  ├── processor.py            # PDF processing logic
  ├── image_extractor.py      # Extract images from PDF
  ├── text_cleaner.py         # Clean text for narration
  └── utils/
      └── pdf_extraction_strategies.py  # Extraction strategies

app/phase2_ai_services/
  ├── openai_client.py        # OpenAI TTS + genre detection
  ├── cartesia_client.py      # Cartesia TTS integration
  ├── book_summary.py         # Book summary generation
  └── pdf_summarizer.py       # PDF summarization

app/phase3_audio_processing/
  └── mastering.py            # Audio quality enhancement

app/phase4_video_generation/
  └── renderer.py             # Video frame generation & rendering
```

#### 4. **Configuration**
- `app/config.py` - All settings, paths, API keys
- `app/logging_config.py` - Logging configuration
- `.env` - **CRITICAL** - Contains API keys (must create on server)

#### 5. **Dependencies**
- `requirements.txt` - All Python packages

#### 6. **Static Assets**
```
assets/
  ├── fonts/
  │   └── Book Antiqua.ttf    # Font for video text
  ├── backgrounds/
  │   ├── 1920x1080-white-solid-color-background.jpg  # 1080p
  │   ├── 854x480-white-background.jpg                # 480p
  │   └── white-paper-texture-background.jpg          # Reels/shorts
  └── pdfs/                    # Optional: sample PDFs
```

### **🟡 IMPORTANT - Should Have:**

- `BACKEND_SETUP.md` - Setup documentation
- `README.md` - Project overview
- `.gitignore` - Keeps secrets safe

### **🟢 OPTIONAL - Nice to Have:**

- `scripts/` - Testing/utility scripts
- `frontend/` - React frontend (if hosting frontend too)
- `jobs/` - Output directory (will be created automatically)

---

## 🏗️ Architecture & Flow

### **API Endpoints:**

#### **Core Endpoints:**
```python
POST   /api/upload              # Upload PDF, start video generation
GET    /api/jobs/{job_id}       # Check job status
GET    /api/jobs                # List all jobs
```

#### **Download Endpoints:**
```python
GET    /api/jobs/{job_id}/download/video          # Download main video
GET    /api/jobs/{job_id}/download/summary        # Download summary text
GET    /api/jobs/{job_id}/download/summary-video  # Download summary video
```

#### **Additional Endpoints:**
```python
POST   /api/jobs/{job_id}/generate-summary-video  # Generate summary video
POST   /api/summarize-pdf                         # Generate summary only
POST   /api/generate-video-from-text              # Video from text
POST   /api/generate-reels-video                  # Generate reels/shorts
GET    /api/cartesia/voices                       # List Cartesia voices
GET    /api/cartesia/models                       # List Cartesia models
```

### **Job Status Flow:**

```
pending → processing → completed
                    ↘ failed
```

**Progress Tracking:**
- 0% - Job created
- 5-15% - PDF extraction
- 20-22% - Text cleaning
- 25-50% - Audio generation
- 55-60% - Audio mastering
- 70-95% - Video rendering
- 100% - Complete

### **Data Storage:**

```
jobs/
  └── {job_id}/
      ├── job_metadata.json         # Status, progress, metadata
      ├── {job_id}_extraction.json  # PDF extraction data
      ├── filtered_pages_X_to_Y.txt # Filtered text
      ├── cleaned_script.txt        # Ready for narration
      ├── raw_audio.mp3             # Initial audio
      ├── timestamps.json           # Word-level timestamps
      ├── processed_audio.mp3       # Mastered audio
      ├── final_video.mp4           # Main video output
      ├── summary.txt               # Book summary (optional)
      └── summary_video/            # Summary video files (optional)
          ├── summary_processed_audio.mp3
          ├── summary_timestamps.json
          └── summary_final_video.mp4
```

---

## 🚀 Deployment Steps

### **Step 1: Prepare Your Server**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# Install ffmpeg (required for video processing)
sudo apt install ffmpeg -y

# Verify installations
python3 --version
ffmpeg -version
```

### **Step 2: Clone/Upload Project**

```bash
# Option A: Clone from Git
git clone <your-repo-url>
cd Pdf_Video_Generation

# Option B: Upload via SCP/SFTP
# Upload the entire Pdf_Video_Generation directory
```

### **Step 3: Create Virtual Environment**

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **Step 4: Configure Environment Variables**

Create `.env` file in project root:

```bash
nano .env
```

Add this content (replace with your actual keys):

```env
# REQUIRED: OpenAI API Key (for TTS, Whisper, GPT)
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE

# OPTIONAL: Cartesia API Key (for alternative TTS)
CARTESIA_API_KEY=your_cartesia_key_here

# OPTIONAL: Serper API Key (for genre detection enhancement)
SERPER_API_KEY=your_serper_key_here

# Video Settings
VIDEO_FPS=30
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
VIDEO_CODEC=libx264

# Text Colors (JSON format)
TEXT_REGULAR_COLOR="[170, 170, 170, 255]"
TEXT_BOLD_COLOR="[0, 0, 0, 255]"
```

**Important:** Make sure `.env` file has correct permissions:
```bash
chmod 600 .env
```

### **Step 5: Verify Assets**

```bash
# Check if assets exist
ls -R assets/

# Expected structure:
# assets/
#   fonts/
#     Book Antiqua.ttf
#   backgrounds/
#     1920x1080-white-solid-color-background.jpg
#     854x480-white-background.jpg
#     white-paper-texture-background.jpg
```

**If fonts/backgrounds are missing**, upload them from your local project.

### **Step 6: Test Backend**

```bash
# Test run (development mode)
python run_backend.py

# Should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
```

Test the health endpoint:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy", "timestamp":"...", ...}
```

### **Step 7: Production Deployment**

#### **Option A: Using systemd (Recommended)**

Create service file:
```bash
sudo nano /etc/systemd/system/pdf-video-api.service
```

Add this configuration:
```ini
[Unit]
Description=PDF to Video API Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Pdf_Video_Generation
Environment="PATH=/path/to/Pdf_Video_Generation/venv/bin"
ExecStart=/path/to/Pdf_Video_Generation/venv/bin/python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-video-api
sudo systemctl start pdf-video-api
sudo systemctl status pdf-video-api
```

#### **Option B: Using Gunicorn + Uvicorn**

Install Gunicorn:
```bash
pip install gunicorn
```

Run with Gunicorn:
```bash
gunicorn app.api.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile /var/log/pdf-video-api/access.log \
  --error-logfile /var/log/pdf-video-api/error.log
```

#### **Option C: Using Docker (if available)**

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t pdf-video-api .
docker run -d -p 8000:8000 --env-file .env -v $(pwd)/jobs:/app/jobs pdf-video-api
```

### **Step 8: Setup Nginx Reverse Proxy (Optional but Recommended)**

Install Nginx:
```bash
sudo apt install nginx -y
```

Create Nginx config:
```bash
sudo nano /etc/nginx/sites-available/pdf-video-api
```

Add configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    client_max_body_size 500M;  # Allow large PDF uploads
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings for long video generation
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/pdf-video-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### **Step 9: SSL Certificate (Optional but Recommended)**

Use Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## 🔧 Environment Configuration

### **Required API Keys:**

1. **OpenAI API Key** (REQUIRED):
   - Used for: TTS generation, Whisper timestamps, GPT summaries
   - Get it: https://platform.openai.com/api-keys
   - Cost: ~$0.015 per minute of audio

2. **Cartesia API Key** (OPTIONAL):
   - Used for: Alternative TTS (higher quality/more voices)
   - Get it: https://cartesia.ai
   - Can work without it (falls back to OpenAI)

3. **Serper API Key** (OPTIONAL):
   - Used for: Enhanced genre detection
   - Get it: https://serper.dev
   - Falls back to basic detection if not provided

### **Path Configuration:**

The `config.py` supports environment variables for AWS/cloud deployment:

```bash
# Optional: Override default paths
export ASSETS_PATH=/custom/path/to/assets
export FONTS_PATH=/custom/path/to/fonts
export BACKGROUNDS_PATH=/custom/path/to/backgrounds
export JOBS_OUTPUT_PATH=/custom/path/to/jobs
```

If not set, defaults to:
- `ASSETS_PATH`: `{project_root}/assets`
- `FONTS_PATH`: `{assets}/fonts`
- `BACKGROUNDS_PATH`: `{assets}/backgrounds`
- `JOBS_OUTPUT_PATH`: `{project_root}/jobs`

### **Video Quality Settings:**

In `.env`, you can adjust:

```env
# For 1080p (default)
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080

# For 480p (faster, smaller files)
# VIDEO_WIDTH=854
# VIDEO_HEIGHT=480
```

---

## 🧪 Testing Your Deployment

### **1. Health Check:**
```bash
curl http://your-server:8000/health
```

### **2. Upload Test:**
```bash
curl -X POST "http://your-server:8000/api/upload" \
  -F "file=@sample.pdf" \
  -F "generate_summary=false" \
  -F "start_page=1" \
  -F "end_page=2"

# Response: {"job_id": "...", "status": "processing", ...}
```

### **3. Check Status:**
```bash
curl http://your-server:8000/api/jobs/{job_id}
```

### **4. Download Video:**
```bash
curl -O http://your-server:8000/api/jobs/{job_id}/download/video
```

---

## 📊 Monitoring & Logs

### **Log Locations:**

```bash
# Job-specific logs
logs/{job_id}.log

# System logs (if using systemd)
sudo journalctl -u pdf-video-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **Check Job Status:**

```bash
# View all jobs
curl http://your-server:8000/api/jobs

# Check specific job metadata
cat jobs/{job_id}/job_metadata.json | jq
```

---

## 🔒 Security Recommendations

1. **Never commit `.env` file** (already in `.gitignore`)
2. **Use HTTPS in production** (setup SSL)
3. **Restrict API access** (add authentication if public)
4. **Set file upload limits** in Nginx config
5. **Use firewall rules** (only open ports 80, 443, 22)

```bash
# UFW firewall example
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 📈 Performance Tips

1. **Use multiple workers** (2-4 based on CPU cores)
2. **Enable caching** for static assets
3. **Use SSD storage** for faster video rendering
4. **Allocate enough RAM** (4GB+ recommended)
5. **Monitor disk space** (videos can be large)

```bash
# Check disk space
df -h

# Monitor CPU/Memory
htop
```

---

## 🆘 Troubleshooting

### **Common Issues:**

1. **"OpenAI API key not found"**
   - Ensure `.env` file exists and has correct key
   - Check file permissions: `ls -la .env`

2. **"FFmpeg not found"**
   - Install: `sudo apt install ffmpeg -y`

3. **"Font file not found"**
   - Upload fonts to `assets/fonts/`
   - Check path in `config.py`

4. **"Job stuck in processing"**
   - Check logs: `cat logs/{job_id}.log`
   - Verify API key has credits

5. **"Video generation fails"**
   - Check disk space: `df -h`
   - Verify ffmpeg works: `ffmpeg -version`

---

## 📞 Support

For issues or questions:
- Check logs in `logs/` directory
- Review job metadata: `jobs/{job_id}/job_metadata.json`
- Test API endpoints individually
- Verify all dependencies installed: `pip list`

---

**Good luck with your deployment! 🚀**
