"""Stream processor: FFmpeg lifecycle, restart logic, and status."""

import asyncio
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

from app.core.config import settings

from .ffmpeg_commands import find_ffmpeg, build_ffmpeg_command


logger = logging.getLogger(__name__)


def _log_monitor(process: subprocess.Popen, log_path: Path) -> None:
    """Background thread: read FFmpeg stdout, write to file, rotate at 1000 lines."""
    try:
        with open(log_path, "w") as f:
            line_count = 0
            for line in process.stdout:
                if line_count >= 1000:
                    f.seek(0)
                    f.truncate()
                    f.write("--- Log Cleared (Limit Reached) ---\n")
                    line_count = 0
                f.write(line)
                f.flush()
                line_count += 1
    except Exception as e:
        logger.error(f"Log monitor thread failed: {e}")


def _tail_log(log_path: Path, lines: int = 8) -> str:
    """Return the last N lines from the FFmpeg log file for quick crash context."""
    try:
        if not log_path.exists():
            return "(ffmpeg log file not found)"

        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()

        return "".join(content[-lines:]).strip() or "(ffmpeg log is empty)"
    except Exception as e:
        return f"(failed to read ffmpeg log: {e})"


class StreamProcessor:
    """FFmpeg wrapper: starts, stops, and auto-restarts the video pipeline."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 50

        self.ffmpeg_path = find_ffmpeg()
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found in PATH!")
        else:
            logger.info(f"Found FFmpeg at: {self.ffmpeg_path}")

        self.hls_dir = Path(settings.HLS_OUTPUT_DIR)
        self.frames_dir = Path(settings.FRAMES_OUTPUT_DIR)
        self.log_file_path = Path("app/storage/ffmpeg.log")

        self.hls_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _build_ffmpeg_command(self) -> list[str]:
        return build_ffmpeg_command(
            ffmpeg_path=self.ffmpeg_path,
            hls_dir=self.hls_dir,
            frames_dir=self.frames_dir,
        )

    async def start(self) -> None:
        if self.is_running:
            logger.warning("Stream processor already running")
            return
        if not self.ffmpeg_path:
            logger.error("Cannot start: FFmpeg not found!")
            return

        logger.info("Cleaning up old HLS files...")
        for file_path in self.hls_dir.glob("*"):
            if file_path.suffix in [".ts", ".m3u8"]:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete old file {file_path}: {e}")

        logger.info("Cleaning up old captured frames...")
        for file_path in self.frames_dir.glob("*.jpg"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete old frame {file_path}: {e}")

        logger.info("Starting stream processor...")
        self.is_running = True
        asyncio.create_task(self._run_ffmpeg())

        print("⏳ Waiting for stream to initialize...")
        hls_path = self.hls_dir / "stream.m3u8"
        for _ in range(30):
            if hls_path.exists():
                print("✅ Stream processor started and ready!")
                return
            await asyncio.sleep(1)
        print("⚠️ Stream processor started, but playlist not yet ready (check logs).")

    async def _run_ffmpeg(self) -> None:
        while self.is_running and self.restart_count < self.max_restarts:
            try:
                cmd = self._build_ffmpeg_command()
                logger.info(f"FFmpeg command: {' '.join(cmd)}")
                logger.info(
                    f"Starting FFmpeg process (attempt {self.restart_count + 1})"
                )

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0,
                )

                log_thread = threading.Thread(
                    target=_log_monitor,
                    args=(self.process, self.log_file_path),
                    daemon=True,
                )
                log_thread.start()

                while self.is_running:
                    if self.process.poll() is not None:
                        crash_context = _tail_log(self.log_file_path)
                        logger.error(
                            "FFmpeg process died (attempt %s). Recent log lines:\n%s",
                            self.restart_count + 1,
                            crash_context,
                        )
                        break
                    await asyncio.sleep(1)

                self.restart_count += 1
                if self.restart_count < self.max_restarts:
                    logger.info(
                        f"Restarting in 5 seconds... ({self.restart_count}/{self.max_restarts})"
                    )
                    await asyncio.sleep(5)
                else:
                    logger.error("Max restart attempts reached. Giving up.")
                    self.is_running = False

            except Exception as e:
                logger.error(f"Error in FFmpeg process: {e}", exc_info=True)
                self.restart_count += 1
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self.is_running = False
        print("✅ Stream processor stopping...")
        if self.process and self.process.poll() is None:
            loop = asyncio.get_running_loop()
            try:
                self.process.terminate()
                await loop.run_in_executor(
                    None,
                    lambda: self.process.wait(timeout=5),
                )
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg not responding, forcing kill")
                self.process.kill()
                await loop.run_in_executor(None, self.process.wait)
            except Exception as e:
                logger.error(f"Error stopping process: {e}")

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "restart_count": self.restart_count,
            "process_alive": self.process.poll() is None if self.process else False,
            "ffmpeg_found": self.ffmpeg_path is not None,
            "ffmpeg_path": self.ffmpeg_path,
        }


stream_processor = StreamProcessor()
