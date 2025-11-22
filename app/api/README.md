# PDF to Video API

FastAPI backend for the PDF-to-Video generation service.

## Features

- Upload PDF files and generate videos
- Optional summary generation (user must select)
- Optional summary video generation (after summary is created)
- Job status tracking
- Download generated videos and summaries
- AWS deployment ready (environment-based paths)

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health check with system info

### Job Management
- `POST /api/upload` - Upload PDF and start video generation
  - Parameters:
    - `file`: PDF file (multipart/form-data)
    - `generate_summary`: boolean (optional, default: false)
    - `start_page`: integer (optional, default: 50)
    - `end_page`: integer (optional, default: 50)
  - Returns: Job ID and status

- `GET /api/jobs/{job_id}` - Get job status
  - Returns: Current job status, message, and metadata

- `GET /api/jobs` - List all jobs
  - Parameters:
    - `limit`: integer (default: 10)
    - `offset`: integer (default: 0)
  - Returns: List of jobs with pagination

### Downloads
- `GET /api/jobs/{job_id}/download/video` - Download main video
- `GET /api/jobs/{job_id}/download/summary` - Download summary text (if available)
- `GET /api/jobs/{job_id}/download/summary-video` - Download summary video (if available)

### Summary Video Generation
- `POST /api/jobs/{job_id}/generate-summary-video` - Generate video from summary
  - Only works if summary was generated for the job

## Job Status Values

- `pending` - Job created, waiting to start
- `processing` - Job is being processed
- `completed` - Job completed successfully
- `failed` - Job failed with error

## Usage Example

### 1. Upload PDF and start video generation
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@book.pdf" \
  -F "generate_summary=false" \
  -F "start_page=50" \
  -F "end_page=50"
```

Response:
```json
{
  "job_id": "book_20251120_1200_abc123",
  "status": "processing",
  "message": "PDF uploaded and pipeline started",
  "created_at": "2025-11-20T12:00:00"
}
```

### 2. Check job status
```bash
curl "http://localhost:8000/api/jobs/book_20251120_1200_abc123"
```

### 3. Download video
```bash
curl "http://localhost:8000/api/jobs/book_20251120_1200_abc123/download/video" \
  -o video.mp4
```

### 4. Generate summary video (if summary exists)
```bash
curl -X POST "http://localhost:8000/api/jobs/book_20251120_1200_abc123/generate-summary-video"
```

## Environment Variables for AWS Deployment

Set these environment variables for AWS deployment:

```bash
ASSETS_PATH=/path/to/assets
FONTS_PATH=/path/to/fonts
BACKGROUNDS_PATH=/path/to/backgrounds
JOBS_OUTPUT_PATH=/path/to/jobs
OPENAI_API_KEY=sk-...
```

## Running the Backend

### Development
```bash
python run_backend.py
```

### Production (with uvicorn)
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

## Workflow

1. **Upload PDF**: User uploads PDF with optional `generate_summary` flag
2. **Main Video**: System generates main video from specified page range
3. **Optional Summary**: If `generate_summary=true`, system generates summary text
4. **Optional Summary Video**: User can request summary video generation after summary is created

## Notes

- Summary generation is **optional** - user must explicitly request it
- Summary video generation is separate - user must request it after summary is generated
- All paths support environment variables for AWS deployment
- Jobs run in background tasks (async processing)

