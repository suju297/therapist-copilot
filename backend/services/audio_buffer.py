"""Simplified audio buffer for WebSocket audio streaming."""

import io
import logging
import os
import tempfile
import wave
from typing import Dict, Any, Optional
from uuid import UUID

import numpy as np

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioBuffer:
    """Buffer for accumulating audio chunks from WebSocket."""
    
    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.chunks = []
        self.chunk_counter = 0
        self.total_samples = 0
        self.sample_rate = settings.audio_sample_rate
        
    def add_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """Add audio chunk to buffer."""
        try:
            # Convert bytes to numpy array
            if len(audio_data) > 0:
                # Assume 16-bit PCM audio
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                self.chunks.append(audio_array)
                self.total_samples += len(audio_array)
            
            self.chunk_counter += 1
            
            # Keep only recent chunks to avoid memory overflow
            max_chunks = 30  # ~30 seconds at 1 second per chunk
            if len(self.chunks) > max_chunks:
                removed_chunk = self.chunks.pop(0)
                self.total_samples -= len(removed_chunk)
            
            duration_seconds = self.total_samples / self.sample_rate
            
            return {
                "chunk_number": self.chunk_counter,
                "buffer_chunks": len(self.chunks),
                "total_samples": self.total_samples,
                "duration_seconds": duration_seconds
            }
            
        except Exception as e:
            logger.error(f"Failed to add audio chunk for session {self.session_id}: {e}")
            return {
                "chunk_number": self.chunk_counter,
                "buffer_chunks": len(self.chunks),
                "total_samples": self.total_samples,
                "duration_seconds": 0.0
            }
    
    def get_combined_audio_file(self, last_n_chunks: int = 3) -> Optional[str]:
        """Get recent audio chunks as a temporary WAV file."""
        try:
            if len(self.chunks) == 0:
                return None
            
            # Get the last N chunks
            recent_chunks = self.chunks[-last_n_chunks:] if len(self.chunks) >= last_n_chunks else self.chunks
            
            if not recent_chunks:
                return None
            
            # Combine chunks
            combined_audio = np.concatenate(recent_chunks)
            
            if len(combined_audio) == 0:
                return None
            
            # Create temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.wav',
                dir=settings.audio_temp_dir,
                delete=False
            )
            
            # Write WAV file
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(combined_audio.astype(np.int16).tobytes())
            
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to create combined audio file for session {self.session_id}: {e}")
            return None
    
    def get_full_audio_file(self) -> Optional[str]:
        """Get all buffered audio as a temporary WAV file."""
        return self.get_combined_audio_file(last_n_chunks=len(self.chunks))
    
    def clear(self):
        """Clear the audio buffer."""
        self.chunks.clear()
        self.total_samples = 0
        logger.info(f"Audio buffer cleared for session {self.session_id}")


# Global audio buffer storage
_audio_buffers: Dict[UUID, AudioBuffer] = {}


def get_audio_buffer(session_id: UUID) -> AudioBuffer:
    """Get or create audio buffer for session."""
    if session_id not in _audio_buffers:
        _audio_buffers[session_id] = AudioBuffer(session_id)
        logger.info(f"Created audio buffer for session {session_id}")
    
    return _audio_buffers[session_id]


def remove_audio_buffer(session_id: UUID):
    """Remove audio buffer for session."""
    if session_id in _audio_buffers:
        _audio_buffers[session_id].clear()
        del _audio_buffers[session_id]
        logger.info(f"Removed audio buffer for session {session_id}")


def get_buffer_stats() -> Dict[str, Any]:
    """Get statistics about all audio buffers."""
    return {
        "active_buffers": len(_audio_buffers),
        "buffers": {
            str(session_id): {
                "chunks": len(buffer.chunks),
                "total_samples": buffer.total_samples,
                "duration_seconds": buffer.total_samples / buffer.sample_rate,
                "chunk_counter": buffer.chunk_counter
            }
            for session_id, buffer in _audio_buffers.items()
        }
    }