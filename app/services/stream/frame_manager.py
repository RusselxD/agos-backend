import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import base64
import aiofiles
from app.core.config import settings

logger = logging.getLogger(__name__)


class FrameManager:
    """
    The 'Librarian' of the video pipeline.
    
    Responsibilities:
    1. RETRIEVAL: Reads the image files created by FFmpeg from the hard drive.
    2. ORGANIZATION: Sorts files by date to find the 'latest' one.
    3. HOUSEKEEPING: Deletes old images so the server hard drive doesn't fill up.
    
    Note: This service DOES NOT create the images. FFmpeg (StreamProcessor) creates them.
    This service only manages them after they exist.
    """
    
    def __init__(self):
        # The folder where FFmpeg drops the 'frame_XXXX.jpg' files
        self.frames_dir = Path(settings.FRAMES_OUTPUT_DIR)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
    

    async def get_latest_frame(self) -> Optional[dict]:
        """
        Picks the newest 'book' off the shelf.
        Used by the Dashboard to show a static preview of the stream.
        """
        try:
            # Glob all .jpg files and sort them (Reverse=True means newest first)
            frames = sorted(self.frames_dir.glob("frame_*.jpg"), reverse=True)

            if not frames:
                return None

            latest_frame = frames[0]

            # Read the binary data from disk
            async with aiofiles.open(latest_frame, 'rb') as f:
                image_data = await f.read()

            # Get file metadata (creation time, size)
            stat = latest_frame.stat()

            return {
                "filename": latest_frame.name,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_bytes": stat.st_size,
                "image_base64": base64.b64encode(image_data).decode('utf-8'),
                "mime_type": "image/jpeg"
            }

        except Exception as e:
            logger.error(f"Error getting latest frame: {e}")
            return None


    async def get_frame_by_filename(self, filename: str) -> Optional[dict]:
        """Get a specific frame by filename"""
        try:
            frame_path = self.frames_dir / filename

            if not frame_path.exists() or not frame_path.is_file():
                return None

            async with aiofiles.open(frame_path, 'rb') as f:
                image_data = await f.read()

            stat = frame_path.stat()

            return {
                "filename": filename,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_bytes": stat.st_size,
                "image_base64": base64.b64encode(image_data).decode('utf-8'),
                "mime_type": "image/jpeg"
            }

        except Exception as e:
            logger.error(f"Error getting frame {filename}: {e}")
            return None


    async def list_frames(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """List all captured frames with pagination"""
        try:
            frames = sorted(self.frames_dir.glob("frame_*.jpg"), reverse=True)

            # Apply pagination
            paginated_frames = frames[offset:offset + limit]

            result = []
            for frame_path in paginated_frames:
                stat = frame_path.stat()
                result.append({
                    "filename": frame_path.name,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                })

            return result

        except Exception as e:
            logger.error(f"Error listing frames: {e}")
            return []


    async def delete_frame(self, filename: str) -> bool:
        """Delete a specific frame"""
        try:
            frame_path = self.frames_dir / filename
            
            if frame_path.exists() and frame_path.is_file():
                frame_path.unlink()
                logger.info(f"Deleted frame: {filename}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting frame {filename}: {e}")
            return False


    async def cleanup_old_frames(self, keep_last_n: int = 100):
        """
        Garbage Collection.
        Deletes old frames to ensure the disk doesn't get full.
        """
        try:
            frames = sorted(self.frames_dir.glob("frame_*.jpg"), reverse=True)

            # Keep the top N, delete the rest
            frames_to_delete = frames[keep_last_n:]

            deleted_count = 0
            for frame_path in frames_to_delete:
                try:
                    frame_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting {frame_path}: {e}")

            logger.info(f"Cleaned up {deleted_count} old frames")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0


frame_manager = FrameManager()