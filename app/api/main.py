"""
FastAPI backend for PDF-to-Video generation service.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import logging
import uuid
import json
from datetime import datetime

from app.config import settings
from app.api.job_service import JobService
from app.api.pipeline_service import PipelineService
from app.api.cartesia_service import CartesiaAPIService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF to Video API",
    description="API for converting PDF books to video with narration",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services - share the same job_service instance
job_service = JobService()
pipeline_service = PipelineService(job_service=job_service)

# Initialize Cartesia API service (may fail if API key not set, that's ok)
try:
    cartesia_api_service = CartesiaAPIService()
except ValueError:
    cartesia_api_service = None
    logger.warning("Cartesia API service not available (API key not configured)")


class JobRequest(BaseModel):
    """Request model for starting a job."""
    generate_summary: bool = False
    start_page: Optional[int] = None
    end_page: Optional[int] = None


class JobResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    message: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None
    progress: Optional[int] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "PDF to Video API is running"}


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "jobs_path": str(settings.JOBS_OUTPUT_PATH)
    }


@app.post("/api/upload", response_model=JobResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    generate_summary: bool = Form(False),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
    voice_provider: str = Form("openai"),
    cartesia_voice_id: Optional[str] = Form(None),
    cartesia_model_id: Optional[str] = Form(None),
):
    """
    Upload a PDF file and start the video generation pipeline.
    
    Args:
        file: PDF file to upload
        generate_summary: Whether to generate a book summary (optional)
        start_page: Optional start page for main video (default: 50)
        end_page: Optional end page for main video (default: 50)
        background_tasks: FastAPI background tasks
    
    Returns:
        JobResponse with job_id and status
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate unique job ID
    job_id = f"{Path(file.filename).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    job_dir = settings.JOBS_OUTPUT_PATH / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Log received parameters
    logger.info(f"Upload parameters - generate_summary: {generate_summary}, start_page: {start_page}, end_page: {end_page}, voice_provider: {voice_provider}, cartesia_voice_id: {cartesia_voice_id}, cartesia_model_id: {cartesia_model_id}")
    
    # Save uploaded PDF
    pdf_path = job_dir / file.filename
    try:
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"PDF uploaded: {pdf_path} (size: {len(content)} bytes)")
    except Exception as e:
        logger.error(f"Failed to save PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {str(e)}")
    
    # Create job record
    job_service.create_job(
        job_id=job_id,
        pdf_path=str(pdf_path),
        generate_summary=generate_summary,
        start_page=start_page or 50,
        end_page=end_page or 50
    )
    
    # Start pipeline in background
    logger.info(f"Starting background pipeline for job {job_id}")
    
    def run_pipeline_wrapper():
        """Wrapper to ensure pipeline runs and logs properly."""
        try:
            logger.info(f"Background task started for job {job_id}")
            pipeline_service.run_pipeline(
                job_id=job_id,
                pdf_path=pdf_path,
                generate_summary=generate_summary,
                start_page=start_page or 50,
                end_page=end_page or 50,
                voice_provider=voice_provider,
                cartesia_voice_id=cartesia_voice_id,
                cartesia_model_id=cartesia_model_id
            )
            logger.info(f"Background task completed for job {job_id}")
        except Exception as e:
            logger.error(f"Background task failed for job {job_id}: {e}", exc_info=True)
            # Try to update job status even if pipeline failed
            try:
                job_service.update_job(
                    job_id=job_id,
                    status="failed",
                    message=f"Pipeline failed: {str(e)}",
                    metadata={"error": str(e)}
                )
            except:
                pass
    
    background_tasks.add_task(run_pipeline_wrapper)
    logger.info(f"Background task added for job {job_id}")
    
    return JobResponse(
        job_id=job_id,
        status="processing",
        message="PDF uploaded and pipeline started",
        created_at=datetime.now().isoformat()
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a job.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        JobResponse with current status
    """
    try:
        # Always reload from disk to get latest progress updates
        # The background task writes to disk, so we need to read from there
        job_service._load_jobs()
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        progress = job.get("progress")
        logger.info(f"Job {job_id} status check - Status: {job.get('status')}, Progress: {progress}, Message: {job.get('message')}")
        
        return JobResponse(
            job_id=job_id,
            status=job.get("status", "unknown"),
            message=job.get("message", ""),
            created_at=job.get("created_at", ""),
            metadata=job.get("metadata", {}),
            progress=progress
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving job status: {str(e)}")


@app.get("/api/jobs/{job_id}/download/video")
async def download_video(job_id: str):
    """
    Download the generated video file.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Video file
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed yet")
    
    video_path = Path(job["metadata"]["final_video_path"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=str(video_path),
        filename=video_path.name,
        media_type="video/mp4"
    )


@app.post("/api/jobs/{job_id}/generate-summary", response_model=JobResponse)
async def generate_summary(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """
    Generate a book summary after main video is complete.
    
    Args:
        job_id: Unique job identifier
        background_tasks: FastAPI background tasks
    
    Returns:
        JobResponse with updated status
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Main video must be completed before generating summary")
    
    # Start summary generation in background
    background_tasks.add_task(
        pipeline_service.generate_summary,
        job_id=job_id
    )
    
    return JobResponse(
        job_id=job_id,
        status="processing",
        message="Summary generation started",
        created_at=job.get("created_at", datetime.now().isoformat()),
        metadata=job.get("metadata")
    )


@app.get("/api/jobs/{job_id}/download/summary")
async def download_summary(job_id: str):
    """
    Download the generated summary file (if available).
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Summary text file
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    summary_path = job.get("metadata", {}).get("summary_path")
    if not summary_path:
        raise HTTPException(status_code=404, detail="Summary not available for this job")
    
    summary_file = Path(summary_path)
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Summary file not found")
    
    return FileResponse(
        path=str(summary_file),
        filename=summary_file.name,
        media_type="text/plain"
    )


@app.post("/api/jobs/{job_id}/generate-summary-video", response_model=JobResponse)
async def generate_summary_video(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """
    Generate a video from the summary (if summary exists).
    
    Args:
        job_id: Unique job identifier
        background_tasks: FastAPI background tasks
    
    Returns:
        JobResponse with updated status
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    summary_path = job.get("metadata", {}).get("summary_path")
    if not summary_path:
        raise HTTPException(status_code=400, detail="Summary not available for this job. Generate summary first.")
    
    summary_file = Path(summary_path)
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Summary file not found")
    
    # Start summary video generation in background
    background_tasks.add_task(
        pipeline_service.generate_summary_video,
        job_id=job_id,
        voice_provider=voice_provider,
        cartesia_voice_id=cartesia_voice_id,
        cartesia_model_id=cartesia_model_id
    )
    
    return JobResponse(
        job_id=job_id,
        status="processing",
        message="Summary video generation started",
        created_at=job.get("created_at", datetime.now().isoformat()),
        metadata=job.get("metadata")
    )


@app.get("/api/jobs/{job_id}/download/summary-video")
async def download_summary_video(job_id: str):
    """
    Download the generated summary video file (if available).
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Summary video file
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    summary_video_path = job.get("metadata", {}).get("summary_video_path")
    if not summary_video_path:
        raise HTTPException(status_code=404, detail="Summary video not available for this job")
    
    summary_video_file = Path(summary_video_path)
    if not summary_video_file.exists():
        raise HTTPException(status_code=404, detail="Summary video file not found")
    
    return FileResponse(
        path=str(summary_video_file),
        filename=summary_video_file.name,
        media_type="video/mp4"
    )


@app.get("/api/jobs")
async def list_jobs(limit: int = 10, offset: int = 0):
    """
    List all jobs with pagination.
    
    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
    
    Returns:
        List of jobs
    """
    jobs = job_service.list_jobs(limit=limit, offset=offset)
    return {"jobs": jobs, "total": len(jobs)}


# ===== CARTESIA API ENDPOINTS =====

@app.get("/api/cartesia/voices")
async def list_cartesia_voices(language: Optional[str] = None, tags: Optional[str] = None):
    """
    List available Cartesia voices.
    
    Args:
        language: Optional language filter (e.g., 'en', 'fr')
        tags: Optional comma-separated tags to filter by (e.g., 'Emotive,Stable')
    
    Returns:
        List of available voices
    """
    if not cartesia_api_service:
        # Return fallback voices even if service is not initialized
        from app.api.cartesia_service import CartesiaAPIService
        try:
            temp_service = CartesiaAPIService()
            voices = temp_service._get_fallback_voices()
            return {"voices": voices, "note": "Using fallback voices (API service not initialized)"}
        except:
            # Last resort: return hardcoded fallback
            voices = [
                {
                    "id": "98a34ef2-2140-4c28-9c71-663dc4dd7022",
                    "name": "Tessa",
                    "language": "en",
                    "tags": ["Emotive", "Expressive"],
                    "description": "Expressive American English voice, great for emotive characters"
                }
            ]
            return {"voices": voices, "note": "Using minimal fallback (API key not configured)"}
    
    tag_list = tags.split(",") if tags else None
    try:
        voices = cartesia_api_service.list_voices(language=language, tags=tag_list)
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Error listing Cartesia voices: {e}", exc_info=True)
        # Return fallback voices on error
        voices = cartesia_api_service._get_fallback_voices()
        return {"voices": voices, "note": f"Using fallback voices due to error: {str(e)}"}


@app.get("/api/cartesia/voices/{voice_id}")
async def get_cartesia_voice(voice_id: str):
    """
    Get details for a specific Cartesia voice.
    
    Args:
        voice_id: Voice ID to retrieve
    
    Returns:
        Voice details
    """
    if not cartesia_api_service:
        raise HTTPException(
            status_code=503,
            detail="Cartesia API service not available. Please configure CARTESIA_API_KEY."
        )
    
    voice = cartesia_api_service.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voice {voice_id} not found")
    
    return voice


@app.get("/api/cartesia/models")
async def list_cartesia_models():
    """
    List available Cartesia TTS models.
    
    Returns:
        List of available models
    """
    if not cartesia_api_service:
        raise HTTPException(
            status_code=503,
            detail="Cartesia API service not available. Please configure CARTESIA_API_KEY."
        )
    
    models = cartesia_api_service.list_models()
    return {"models": models}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

