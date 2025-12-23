# app/services/stream/stream_processor.py
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import signal
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)


class StreamProcessor:
    """
    The 'Engine Room' of the video pipeline.
    
    Responsibilities:
    1. WRAPPER: Wraps the external 'ffmpeg.exe' binary so Python can control it.
    2. LIFECYCLE: Starts, stops, and auto-restarts the video processing job.
    3. PROCESSING: Tells FFmpeg to take ONE input stream and split it into TWO outputs:
       - Output A: HLS Video segments (.ts files) for the web player.
       - Output B: Periodic snapshots (.jpg files) for the ML Service.
    """
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 50
        
        # 1. Locate the FFmpeg tool on the host OS
        self.ffmpeg_path = self._find_ffmpeg()
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found in PATH!")
        else:
            logger.info(f"Found FFmpeg at: {self.ffmpeg_path}")
        
        # 2. Prepare the workspace (Storage Folders)
        # These folders effectively act as the "Buffer" between FFmpeg and the API/ML Service.
        self.hls_dir = Path(settings.HLS_OUTPUT_DIR)
        self.frames_dir = Path(settings.FRAMES_OUTPUT_DIR)
        self.hls_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Helper to find where ffmpeg.exe is installed on the system."""
        # Check explicit path in config
        if Path(settings.FFMPEG_PATH).exists():
            return settings.FFMPEG_PATH
        
        # Check system PATH environment variable
        ffmpeg_path = shutil.which(settings.FFMPEG_PATH)
        if ffmpeg_path:
            return ffmpeg_path
        
        logger.error(f"FFmpeg not found at: {settings.FFMPEG_PATH}")
        return None
    
    def _build_ffmpeg_command(self) -> list[str]:
        """
        Constructs the complex command-line string to launch FFmpeg.
        
        This is the most critical logic. It translates our python settings
        into arguments that FFmpeg understands.
        """
        
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg not found!")
        
        # Define where the outputs will land on the hard drive
        hls_path = self.hls_dir / "stream.m3u8"
        # Pattern %Y%m%d... tells FFmpeg to auto-name files by current time
        frame_pattern = self.frames_dir / "frame_%Y%m%d_%H%M%S.jpg"
        
        cmd = [
            self.ffmpeg_path,
            
            # --- INPUT CONFIGURATION ---
            '-re',                      # Read input at native frame rate (don't rush)
            '-i', settings.STREAM_URL,  # The Source (RTSP/RTMP/HTTP)
            
            # Resilience: Keep trying to connect if network blips
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '10',
            
            # --- OUTPUT 1: HLS STREAM (For Frontend) ---
            # This allows the web browser to play the video.
            '-map', '0:v',             # Take video track from input 0
            '-c:v', 'libx264',         # Codec: H.264 (Standard web video)
            '-preset', 'ultrafast',    # Speed: Sacrifice compression for low CPU usage
            
            # Keyframe Logic: Force a "cut point" exactly every X frames.
            # This ensures segments are perfectly aligned for the player.
            '-g', str(settings.HLS_TIME * 30), 
            '-sc_threshold', '0',      # Disable scene detection (keeps timing constant)
            
            '-f', 'hls',               # Format: Apple HLS
            '-hls_time', str(settings.HLS_TIME),       # Segment length (e.g., 6s)
            '-hls_list_size', str(settings.HLS_LIST_SIZE), # Keep only last 5 segments
            '-hls_flags', 'delete_segments+append_list',   # Delete old segments to save disk space
            '-hls_segment_filename', str(self.hls_dir / 'segment_%03d.ts'),
            str(hls_path),             # The "Menu" file (.m3u8)
            
            # --- OUTPUT 2: SNAPSHOTS (For ML Service) ---
            # This grabs still images for analysis.
            '-map', '0:v',             # Take video track again
            '-vf', f'fps=1/{settings.FRAME_CAPTURE_INTERVAL_SECONDS},scale={settings.FRAME_WIDTH}:{settings.FRAME_HEIGHT}',
                                       # Filter: Take 1 frame every X seconds + Resize
            '-q:v', str(settings.FRAME_QUALITY), # Jpeg Quality
            '-f', 'image2',            # Format: Image Sequence
            '-strftime', '1',          # Allow using time patterns in filename
            str(frame_pattern),        # Output path template
        ]
        
        return cmd
    
    async def start(self):
        """
        The 'Ignition Switch'.
        Cleans up old mess and starts the engine.
        """
        if self.is_running:
            logger.warning("Stream processor already running")
            return
        
        if not self.ffmpeg_path:
            logger.error("Cannot start: FFmpeg not found!")
            return

        # 1. CLEANUP: Delete old HLS files
        # If we don't do this, the video player might see old files from yesterday
        # and get confused (Time Jump/404s).
        logger.info("Cleaning up old HLS files...")
        for file_path in self.hls_dir.glob("*"):
            if file_path.suffix in ['.ts', '.m3u8']:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete old file {file_path}: {e}")
        
        logger.info("Starting stream processor...")
        self.is_running = True
        
        # 2. BACKGROUND TASK: Run the process loop without blocking Python
        asyncio.create_task(self._run_ffmpeg())
    
    async def _run_ffmpeg(self):
        """
        The 'Monitor'.
        Keeps the FFmpeg process running. If it crashes, it restarts it.
        """
        while self.is_running and self.restart_count < self.max_restarts:
            try:
                cmd = self._build_ffmpeg_command()
                
                logger.info(f"Starting FFmpeg process (attempt {self.restart_count + 1})")
                
                # 3. LAUNCH: Redirect stdout/stderr to file to prevent buffer deadlocks
                log_path = Path("app/storage/ffmpeg.log")
                with open(log_path, "w") as log_file:
                    self.process = subprocess.Popen(
                        cmd,
                        stdout=log_file,      # Write logs to file
                        stderr=subprocess.STDOUT, # Merge errors into same file
                        universal_newlines=True,
                        shell=False,
                        # Windows specific: Don't pop up a black CMD window
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    # 4. WATCH: Check every second if it's still alive
                    while self.is_running:
                        if self.process.poll() is not None:
                            # Process died! Break loop to trigger restart logic
                            logger.error(f"FFmpeg process died. Check logs at: {log_path}")
                            break
                        
                        await asyncio.sleep(1)
                
                # If we get here, the process died.
                self.restart_count += 1
                
                if self.restart_count < self.max_restarts:
                    logger.info(f"Restarting in 5 seconds... ({self.restart_count}/{self.max_restarts})")
                    await asyncio.sleep(5)
                else:
                    logger.error("Max restart attempts reached. Giving up.")
                    self.is_running = False
                    
            except Exception as e:
                logger.error(f"Error in FFmpeg process: {e}", exc_info=True)
                self.restart_count += 1
                await asyncio.sleep(5)
    
    async def stop(self):
        """Gracefully shuts down the FFmpeg process."""
        logger.info("Stopping stream processor...")
        self.is_running = False
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg not responding, forcing kill")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
        
        logger.info("Stream processor stopped")
    
    def get_status(self) -> dict:
        """Returns the health status of the processor."""
        return {
            "is_running": self.is_running,
            "restart_count": self.restart_count,
            "process_alive": self.process.poll() is None if self.process else False,
            "ffmpeg_found": self.ffmpeg_path is not None,
            "ffmpeg_path": self.ffmpeg_path,
        }


# Global instance
stream_processor = StreamProcessor()