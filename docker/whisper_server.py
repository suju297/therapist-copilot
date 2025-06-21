#!/usr/bin/env python3
"""Whisper HTTP server for speech-to-text transcription."""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper STT Service", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whisper"}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Transcribe audio file using Whisper."""
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"Processing audio file: {file.filename} ({len(content)} bytes)")
        
        # Find Whisper model
        model_path = os.environ.get("WHISPER_MODEL_PATH", "/models/ggml-large-v3.bin")
        
        # Try alternative model paths if the default doesn't exist
        if not os.path.exists(model_path):
            alternative_paths = [
                "/models/ggml-base.en.bin",
                "/models/ggml-small.en.bin",
                "/models/ggml-medium.en.bin"
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    model_path = alt_path
                    break
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="No Whisper model found. Please ensure models are available."
                )
        
        logger.info(f"Using Whisper model: {model_path}")
        
        # Run Whisper transcription
        cmd = [
            "/usr/local/bin/whisper",
            "-m", model_path,
            "-f", tmp_file_path,
            "-t", "4",  # Use 4 threads
            "-l", "en",  # Language: English
            "--output-json",
            "--no-timestamps"  # Disable timestamps for cleaner output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Clean up temp file
        try:
            os.unlink(tmp_file_path)
        except:
            pass
        
        if result.returncode != 0:
            logger.error(f"Whisper failed: {result.stderr}")
            raise HTTPException(
                status_code=500, 
                detail=f"Transcription failed: {result.stderr}"
            )
        
        # Parse Whisper output
        output_lines = result.stdout.strip().split('\n')
        transcript_text = ""
        segments = []
        
        # Extract transcript text from output
        for line in output_lines:
            line = line.strip()
            if line and not line.startswith('[') and not line.startswith('whisper_'):
                # Clean up the line
                if ']' in line:
                    # Remove timestamp markers if present
                    line = line.split(']', 1)[-1].strip()
                
                if line:
                    transcript_text += line + " "
                    
                    # Create a segment for compatibility
                    segments.append({
                        "start": 0.0,
                        "end": 0.0,
                        "text": line
                    })
        
        transcript_text = transcript_text.strip()
        
        # Estimate confidence (Whisper doesn't provide confidence scores)
        confidence = 0.8 if transcript_text else 0.0
        
        # Calculate duration (rough estimate)
        duration = len(content) / (16000 * 2)  # Assuming 16kHz, 16-bit audio
        
        response = {
            "text": transcript_text,
            "language": "en",
            "duration": duration,
            "segments": segments,
            "confidence": confidence
        }
        
        logger.info(f"Transcription completed: '{transcript_text[:100]}...'")
        return response
        
    except subprocess.TimeoutExpired:
        logger.error("Transcription timeout")
        try:
            os.unlink(tmp_file_path)
        except:
            pass
        raise HTTPException(status_code=408, detail="Transcription timeout")
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        try:
            os.unlink(tmp_file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.get("/models")
async def list_models():
    """List available Whisper models."""
    
    models_dir = "/models"
    available_models = []
    
    if os.path.exists(models_dir):
        for file in os.listdir(models_dir):
            if file.endswith('.bin'):
                file_path = os.path.join(models_dir, file)
                file_size = os.path.getsize(file_path)
                available_models.append({
                    "name": file,
                    "path": file_path,
                    "size_mb": round(file_size / 1024 / 1024, 2)
                })
    
    return {
        "models": available_models,
        "models_directory": models_dir,
        "current_model": os.environ.get("WHISPER_MODEL_PATH", "/models/ggml-large-v3.bin")
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Whisper STT Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "transcribe": "/transcribe",
            "health": "/health",
            "models": "/models"
        }
    }


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting Whisper STT service on port {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )