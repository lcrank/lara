"""
Whisper Service - Speech-to-Text using Groq Whisper API
"""

import logging
import io
from typing import NamedTuple
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class TranscriptionResult(NamedTuple):
    text: str
    confidence: float

class WhisperService:
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)
        self.model = "whisper-large-v3"
    
    async def transcribe(self, audio_data: bytes, language: str = "en") -> TranscriptionResult:
        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.ogg"
            
            logger.debug(f"Calling Groq Whisper API")
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=("audio.ogg", audio_file),
                response_format="verbose_json"
            )
            
            text = response.text.strip()
            confidence = 0.95 
            
            logger.info(f"Transcribed: '{text}'")
            return TranscriptionResult(text=text, confidence=confidence)
        
        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}", exc_info=e)
            raise
