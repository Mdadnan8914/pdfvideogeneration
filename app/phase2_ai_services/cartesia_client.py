import json
import logging
import os
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import subprocess
import shutil
import requests

from app.config import settings

logger = logging.getLogger(__name__)

# Suppress Pydantic V1 compatibility warning with Python 3.14+
# This is a known issue in Cartesia library, doesn't affect functionality
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*", category=UserWarning)

try:
    from cartesia import Cartesia
    CARTESIA_AVAILABLE = True
except ImportError:
    CARTESIA_AVAILABLE = False
    logger.warning("Cartesia Python SDK not installed. Install with: pip install cartesia")


class CartesiaService:
    """Service for Cartesia API integration (TTS with timestamps)."""

    def __init__(self, voice_id: str = "98a34ef2-2140-4c28-9c71-663dc4dd7022", model_id: str = "sonic-3"):
        """
        Initialize Cartesia service.
        
        Args:
            voice_id: Cartesia voice ID (default: Tessa - expressive voice)
            model_id: Cartesia model ID (default: sonic-3)
        """
        if not CARTESIA_AVAILABLE:
            raise ImportError(
                "Cartesia Python SDK not installed. "
                "Please install it with: pip install cartesia"
            )
        
        api_key = settings.CARTESIA_API_KEY or os.getenv('CARTESIA_API_KEY', '')
        
        if not api_key:
            raise ValueError(
                "Cartesia API key not configured. "
                "Please set CARTESIA_API_KEY in your .env file or environment variables."
            )
        
        self.client = Cartesia(api_key=api_key)
        self.voice_id = voice_id
        self.model_id = model_id
        logger.info(f"CartesiaService initialized (Voice ID: {self.voice_id}, Model: {self.model_id})")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 1 token = 4 characters for English)."""
        return len(text) // 4
    
    def _split_text_into_chunks(self, text: str, max_tokens: int = 2000) -> List[str]:
        """
        Split text into chunks that fit within token limits.
        Cartesia can handle longer texts, but we'll chunk for safety.
        """
        if self._estimate_tokens(text) <= max_tokens:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append('. '.join(current_chunk))
        
        return chunks

    def _get_ffmpeg_path(self) -> str:
        """Get the path to ffmpeg executable."""
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
        
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        raise FileNotFoundError("FFmpeg not found. Please install ffmpeg.")

    def _generate_audio_bytes(self, text: str, output_path: Path) -> Path:
        """
        Generate audio using Cartesia TTS bytes endpoint.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            
        Returns:
            Path to generated audio file
        """
        logger.info(f"Generating audio with Cartesia TTS (model: {self.model_id}, voice: {self.voice_id})...")
        
        # Generate audio using bytes endpoint (for file output)
        chunk_iter = self.client.tts.bytes(
            model_id=self.model_id,
            transcript=text,
            voice={
                "mode": "id",
                "id": self.voice_id,
            },
            output_format={
                "container": "wav",
                "sample_rate": 44100,
                "encoding": "pcm_f32le",
            },
        )
        
        # Write audio chunks to file
        with open(output_path, "wb") as f:
            for chunk in chunk_iter:
                f.write(chunk)
        
        logger.info(f"Audio saved to {output_path}")
        return output_path

    def _get_timestamps_whisper(self, audio_path: Path) -> Dict:
        """
        Get word-level timestamps using OpenAI Whisper (same as OpenAI service).
        This transcribes the generated audio to get accurate timestamps.
        
        Args:
            audio_path: Path to the generated audio file
            
        Returns:
            Dictionary with words and segments in OpenAI-compatible format
        """
        logger.info("Getting timestamps using OpenAI Whisper...")
        
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI library is required for Whisper transcription. Install with: pip install openai")
        
        # Use OpenAI Whisper to transcribe the audio and get timestamps
        # This is the same approach used by OpenAIService
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        with open(audio_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        timestamps_data = transcription.model_dump()
        
        logger.info(f"Whisper transcription complete: {len(timestamps_data.get('words', []))} words, {len(timestamps_data.get('segments', []))} segments")
        
        return timestamps_data


    def generate_audio_with_timestamps(
        self, 
        text: str, 
        output_dir: Path,
        job_id: str,
        genre: str = "general"
    ) -> Tuple[Path, Path]:
        """
        Generate audio and timestamps using Cartesia TTS.
        
        Args:
            text: Text to convert to speech
            output_dir: Directory to save output files
            job_id: Job ID for logging
            genre: Book genre (not used by Cartesia, kept for compatibility)
            
        Returns:
            Tuple of (audio_path, timestamps_path)
        """
        audio_path = output_dir / "audio_raw.wav"
        timestamps_path = output_dir / "timestamps.json"
        
        try:
            # Split text into chunks if needed
            chunks = self._split_text_into_chunks(text, max_tokens=2000)
            
            if len(chunks) > 1:
                logger.info(f"Job {job_id}: Text exceeds limit, splitting into {len(chunks)} chunks...")
                return self._process_chunked_text(chunks, audio_path, timestamps_path, job_id)
            else:
                # Single chunk - process normally
                return self._process_single_chunk(text, audio_path, timestamps_path, job_id)
        
        except Exception as e:
            logger.error(f"Job {job_id}: Error in Cartesia TTS Pipeline!", exc_info=True)
            raise

    def _process_single_chunk(
        self, 
        text: str, 
        audio_path: Path, 
        timestamps_path: Path,
        job_id: str
    ) -> Tuple[Path, Path]:
        """Process a single text chunk."""
        # Generate audio
        self._generate_audio_bytes(text, audio_path)
        
        # Get timestamps using Whisper (transcribe the generated audio)
        timestamps_data = self._get_timestamps_whisper(audio_path)
        
        # Save timestamps
        with open(timestamps_path, "w", encoding="utf-8") as f:
            json.dump(timestamps_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Job {job_id}: Audio and timestamps saved")
        
        return audio_path, timestamps_path

    def _process_chunked_text(
        self,
        chunks: List[str],
        audio_path: Path,
        timestamps_path: Path,
        job_id: str
    ) -> Tuple[Path, Path]:
        """Process multiple text chunks and combine results."""
        chunk_audio_files = []
        all_words = []
        all_segments = []
        total_duration = 0.0
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            logger.info(f"Job {job_id}: Processing chunk {i+1}/{len(chunks)}...")
            chunk_audio_raw = audio_path.parent / f"{audio_path.stem}_chunk_{i}_raw.wav"
            chunk_audio = audio_path.parent / f"{audio_path.stem}_chunk_{i}.wav"
            
            # Generate audio for chunk
            self._generate_audio_bytes(chunk, chunk_audio_raw)
            
            # Normalize and clean each chunk before concatenation
            # This prevents static noise from level mismatches
            ffmpeg_path = self._get_ffmpeg_path()
            normalize_cmd = [
                ffmpeg_path,
                "-y",
                "-i", str(chunk_audio_raw),
                "-af", "highpass=f=90,lowpass=f=16000,afftdn=nf=-25,anlmdn=s=0.0001",  # Remove low-freq static, denoise
                "-ar", "44100",
                "-ac", "1",
                "-c:a", "pcm_f32le",
                str(chunk_audio)
            ]
            subprocess.run(normalize_cmd, check=True, capture_output=True, text=True)
            
            # Clean up raw chunk
            if chunk_audio_raw.exists():
                chunk_audio_raw.unlink()
            
            chunk_audio_files.append(chunk_audio)
            
            # Get timestamps for chunk using Whisper
            chunk_timestamps = self._get_timestamps_whisper(chunk_audio)
            
            # Adjust timestamps with offset
            if "words" in chunk_timestamps:
                for word in chunk_timestamps["words"]:
                    word["start"] += total_duration
                    word["end"] += total_duration
                all_words.extend(chunk_timestamps["words"])
            
            if "segments" in chunk_timestamps:
                for segment in chunk_timestamps["segments"]:
                    segment["start"] += total_duration
                    segment["end"] += total_duration
                all_segments.extend(chunk_timestamps["segments"])
            
            # Update total duration
            if chunk_timestamps.get("duration"):
                total_duration += chunk_timestamps["duration"]
            elif all_segments:
                total_duration = all_segments[-1]["end"]
        
        # Combine audio files using ffmpeg
        logger.info(f"Job {job_id}: Combining {len(chunk_audio_files)} audio chunks...")
        ffmpeg_path = self._get_ffmpeg_path()
        
        # Create concat file for ffmpeg
        concat_file = audio_path.parent / "concat_list.txt"
        with open(concat_file, "w") as f:
            for chunk_file in chunk_audio_files:
                f.write(f"file '{chunk_file.absolute()}'\n")
        
        # Concatenate audio files with normalization and smooth transitions
        # Normalize all chunks to same level and re-encode for smooth boundaries
        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=90,lowpass=f=16000",  # Normalize and remove static
            "-c:a", "pcm_f32le",
            "-ar", "44100",
            "-ac", "1",
            str(audio_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Clean up chunk files and concat file
        for chunk_file in chunk_audio_files:
            if chunk_file.exists():
                chunk_file.unlink()
        if concat_file.exists():
            concat_file.unlink()
        
        # Save combined timestamps
        combined_data = {
            "text": " ".join(chunks),
            "language": "en",
            "duration": total_duration,
            "words": all_words,
            "segments": all_segments
        }
        
        with open(timestamps_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Job {job_id}: Combined audio and timestamps saved")
        
        return audio_path, timestamps_path

