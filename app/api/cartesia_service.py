"""
Cartesia API service for voice and model management.
"""
import logging
import os
import warnings
from typing import List, Dict, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Suppress Pydantic V1 compatibility warning with Python 3.14+
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality isn't compatible with Python 3.14.*", category=UserWarning)

try:
    from cartesia import Cartesia
    CARTESIA_AVAILABLE = True
except ImportError:
    CARTESIA_AVAILABLE = False
    logger.warning("Cartesia Python SDK not installed. Install with: pip install cartesia")


class CartesiaAPIService:
    """Service for interacting with Cartesia API endpoints."""
    
    def __init__(self):
        """Initialize Cartesia API service."""
        if not CARTESIA_AVAILABLE:
            raise ImportError(
                "Cartesia Python SDK not installed. "
                "Please install it with: pip install cartesia"
            )
        
        self.api_key = settings.CARTESIA_API_KEY or os.getenv('CARTESIA_API_KEY', '')
        if not self.api_key:
            raise ValueError(
                "Cartesia API key not configured. "
                "Please set CARTESIA_API_KEY in your .env file or environment variables."
            )
        
        try:
            self.client = Cartesia(api_key=self.api_key)
            logger.info("CartesiaAPIService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Cartesia client: {e}", exc_info=True)
            raise
    
    def list_voices(self, language: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List available Cartesia voices.
        
        Args:
            language: Optional language filter (e.g., 'en', 'fr')
            tags: Optional list of tags to filter by (e.g., ['Emotive', 'Stable'])
        
        Returns:
            List of voice dictionaries with id, name, language, tags, etc.
        """
        try:
            # Try using the Cartesia SDK if it has a voices method
            # If not available, fall back to known voices
            if hasattr(self.client, 'voices') and hasattr(self.client.voices, 'list'):
                try:
                    voices_response = self.client.voices.list()
                    voices = []
                    # Convert SDK response to our format
                    if hasattr(voices_response, 'data'):
                        for voice in voices_response.data:
                            voice_dict = {
                                "id": getattr(voice, 'id', ''),
                                "name": getattr(voice, 'name', ''),
                                "language": getattr(voice, 'language', 'en'),
                                "tags": getattr(voice, 'tags', []),
                                "description": getattr(voice, 'description', '')
                            }
                            # Apply filters
                            if language and voice_dict.get("language") != language:
                                continue
                            if tags and not any(tag in voice_dict.get("tags", []) for tag in tags):
                                continue
                            voices.append(voice_dict)
                    
                    if voices:
                        logger.info(f"Retrieved {len(voices)} voices from Cartesia SDK")
                        return voices
                except Exception as sdk_error:
                    logger.warning(f"Cartesia SDK voices.list() failed: {sdk_error}, using fallback")
            
            # If SDK method doesn't exist or failed, use fallback
            logger.info("Using fallback voices list (Cartesia API may not have a voices endpoint)")
            return self._get_fallback_voices()
            
        except Exception as e:
            logger.error(f"Error fetching voices: {e}", exc_info=True)
            return self._get_fallback_voices()
    
    def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific voice.
        
        Args:
            voice_id: Voice ID to retrieve
        
        Returns:
            Voice dictionary with details, or None if not found
        """
        try:
            # Try using SDK first
            if hasattr(self.client, 'voices') and hasattr(self.client.voices, 'get'):
                try:
                    voice = self.client.voices.get(voice_id)
                    if voice:
                        return {
                            "id": getattr(voice, 'id', voice_id),
                            "name": getattr(voice, 'name', ''),
                            "language": getattr(voice, 'language', 'en'),
                            "tags": getattr(voice, 'tags', []),
                            "description": getattr(voice, 'description', ''),
                            "gender": getattr(voice, 'gender', '')
                        }
                except Exception as sdk_error:
                    logger.warning(f"Cartesia SDK voices.get() failed: {sdk_error}, checking fallback list")
            
            # Fallback: search in known voices
            fallback_voices = self._get_fallback_voices()
            for voice in fallback_voices:
                if voice.get("id") == voice_id:
                    return voice
            
            logger.warning(f"Voice {voice_id} not found in fallback list")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching voice {voice_id}: {e}", exc_info=True)
            # Try fallback
            fallback_voices = self._get_fallback_voices()
            for voice in fallback_voices:
                if voice.get("id") == voice_id:
                    return voice
            return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available Cartesia TTS models.
        
        Returns:
            List of model dictionaries
        """
        # Cartesia models are typically documented, not via API
        # Return known models
        return [
            {
                "id": "sonic-3",
                "name": "Sonic 3",
                "description": "Latest streaming TTS model with high naturalness and accurate transcript following",
                "languages": ["en", "fr", "de", "es", "pt", "zh", "ja", "hi", "it", "ko", "nl", "pl", "ru", "sv", "tr", "tl", "bg", "ro", "ar", "cs", "el", "fi", "hr", "ms", "sk", "da", "ta", "uk", "hu", "no", "vi", "bn", "th", "he", "ka", "id", "te", "gu", "kn", "ml", "mr", "pa"],
                "features": ["volume_control", "speed_control", "emotion_control", "laughter_tags"]
            },
            {
                "id": "sonic-3-2025-10-27",
                "name": "Sonic 3 (2025-10-27)",
                "description": "Pinned snapshot of Sonic 3 from October 27, 2025",
                "languages": ["en", "fr", "de", "es", "pt", "zh", "ja", "hi", "it", "ko", "nl", "pl", "ru", "sv", "tr", "tl", "bg", "ro", "ar", "cs", "el", "fi", "hr", "ms", "sk", "da", "ta", "uk", "hu", "no", "vi", "bn", "th", "he", "ka", "id", "te", "gu", "kn", "ml", "mr", "pa"],
                "features": ["volume_control", "speed_control", "emotion_control", "laughter_tags"]
            }
        ]
    
    def _get_fallback_voices(self) -> List[Dict[str, Any]]:
        """
        Return a curated list of known Cartesia voices as fallback.
        Based on Cartesia documentation.
        """
        return [
            {
                "id": "98a34ef2-2140-4c28-9c71-663dc4dd7022",
                "name": "Tessa",
                "language": "en",
                "gender": "female",
                "tags": ["Emotive", "Expressive"],
                "description": "Expressive American English voice, great for emotive characters"
            },
            {
                "id": "c961b81c-a935-4c17-bfb3-ba2239de8c2f",
                "name": "Kyle",
                "language": "en",
                "gender": "male",
                "tags": ["Emotive", "Expressive"],
                "description": "Expressive American English voice, great for emotive characters"
            },
            {
                "id": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
                "name": "Katie",
                "language": "en",
                "gender": "female",
                "tags": ["Stable", "Realistic"],
                "description": "Stable, realistic American English voice, great for voice agents"
            },
            {
                "id": "228fca29-3a0a-435c-8728-5cb483251068",
                "name": "Kiefer",
                "language": "en",
                "gender": "male",
                "tags": ["Stable", "Realistic"],
                "description": "Stable, realistic American English voice, great for voice agents"
            },
            {
                "id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",
                "name": "Tessa (Alternative)",
                "language": "en",
                "gender": "female",
                "tags": ["Emotive"],
                "description": "Emotive American English voice"
            }
        ]

