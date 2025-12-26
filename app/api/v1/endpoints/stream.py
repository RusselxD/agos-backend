import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pathlib import Path

from app.schemas import StreamStatus, FrameResponse, FrameListResponse

from app.services.stream import stream_processor, frame_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/status", response_model=StreamStatus)
async def get_stream_status():
    """Get current status of the stream processor"""
    status = stream_processor.get_status()
    
    return StreamStatus(
        **status,
        stream_url=settings.STREAM_URL,
        hls_endpoint="/api/v1/stream/hls/stream.m3u8"
    )

@router.post("/start")
async def start_stream():
    """Start the stream processor"""
    try:
        await stream_processor.start()
        return {"message": "Stream processor started", "success": True}
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_stream():
    """Stop the stream processor"""
    try:
        await stream_processor.stop()
        return {"message": "Stream processor stopped", "success": True}
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frames/latest", response_model=FrameResponse)
async def get_latest_frame():
    """Get the most recently captured frame"""
    frame = await frame_manager.get_latest_frame()
    
    if not frame:
        raise HTTPException(status_code=404, detail="No frames captured yet")
    
    return frame


@router.get("/frames", response_model=FrameListResponse)
async def list_frames(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all captured frames with pagination"""
    frames = await frame_manager.list_frames(limit=limit, offset=offset)
    
    # Get total count
    frames_dir = Path(settings.FRAMES_OUTPUT_DIR)
    total = len(list(frames_dir.glob("frame_*.jpg")))
    
    return FrameListResponse(
        frames=frames,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/frames/{filename}")
async def get_frame_by_filename(filename: str):
    """Get a specific frame by filename (returns image file)"""
    frame_path = Path(settings.FRAMES_OUTPUT_DIR) / filename
    
    if not frame_path.exists() or not frame_path.is_file():
        raise HTTPException(status_code=404, detail="Frame not found")
    
    return FileResponse(
        frame_path,
        media_type="image/jpeg",
        filename=filename
    )


@router.delete("/frames/{filename}")
async def delete_frame(filename: str):
    """Delete a specific frame"""
    success = await frame_manager.delete_frame(filename)
    
    if not success:
        raise HTTPException(status_code=404, detail="Frame not found")
    
    return {"message": f"Frame {filename} deleted", "success": True}


@router.post("/frames/cleanup")
async def cleanup_old_frames(keep_last: int = Query(100, ge=10, le=1000)):
    """Cleanup old frames, keeping only the most recent N"""
    deleted_count = await frame_manager.cleanup_old_frames(keep_last_n=keep_last)
    
    return {
        "message": f"Cleaned up {deleted_count} old frames",
        "deleted_count": deleted_count,
        "success": True
    }


# HLS Stream endpoints (serve HLS files)
@router.api_route("/hls/{filename}", methods=["GET", "HEAD"])
async def serve_hls_file(filename: str):
    """Serve HLS playlist or segment files"""
    hls_path = Path(settings.HLS_OUTPUT_DIR) / filename
    
    if not hls_path.exists():
        raise HTTPException(status_code=404, detail="HLS file not found")
    
    # Determine content type
    if filename.endswith('.m3u8'):
        media_type = "application/vnd.apple.mpegurl"
        # Read file into memory to avoid Content-Length mismatch if file changes
        try:
            content = hls_path.read_text(encoding="utf-8")
            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        except Exception as e:
            logger.error(f"Error reading HLS playlist: {e}")
            raise HTTPException(status_code=500, detail="Error reading playlist")

    elif filename.endswith('.ts'):
        media_type = "video/mp2t"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        hls_path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )