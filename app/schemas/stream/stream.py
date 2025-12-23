# app/schemas/stream/stream.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StreamStatus(BaseModel):
    """Stream processor status"""
    is_running: bool
    restart_count: int
    process_alive: bool
    stream_url: str
    hls_endpoint: str


class FrameResponse(BaseModel):
    """Single frame response with image data"""
    filename: str
    timestamp: str
    size_bytes: int
    image_base64: str
    mime_type: str = "image/jpeg"


class FrameListItem(BaseModel):
    """Frame metadata without image data"""
    filename: str
    timestamp: str
    size_bytes: int


class FrameListResponse(BaseModel):
    """Paginated list of frames"""
    frames: List[FrameListItem]
    total: int
    limit: int
    offset: int