"""FFmpeg binary detection and command construction."""

import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings


def find_ffmpeg() -> Optional[str]:
    """Locate FFmpeg binary (config path or system PATH)."""
    if Path(settings.FFMPEG_PATH).exists():
        return settings.FFMPEG_PATH
    ffmpeg_path = shutil.which(settings.FFMPEG_PATH)
    return ffmpeg_path if ffmpeg_path else None


def build_ffmpeg_command(
    ffmpeg_path: Optional[str],
    hls_dir: Path,
    frames_dir: Path,
) -> list[str]:
    """Build FFmpeg command for HLS + frame capture."""
    if not ffmpeg_path:
        raise RuntimeError("FFmpeg not found!")
    hls_path = hls_dir / "stream.m3u8"
    frame_pattern = frames_dir / "frame_%Y%m%d_%H%M%S.jpg"

    cmd = [ffmpeg_path]

    if settings.STREAM_URL.lower().startswith("rtsp"):
        cmd.extend(["-rtsp_transport", "tcp"])

    cmd.extend([
        "-i", settings.STREAM_URL,
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "10",
        "-map", "0:v",
        "-c:v", "copy",
        "-f", "hls",
        "-hls_time", str(settings.HLS_TIME),
        "-hls_list_size", str(settings.HLS_LIST_SIZE),
        "-hls_flags", "delete_segments",
        "-hls_segment_filename", str(hls_dir / "segment_%03d.ts"),
        str(hls_path),
        "-map", "0:v",
        "-vf", f"fps=1/{settings.FRAME_CAPTURE_INTERVAL_SECONDS},scale={settings.FRAME_WIDTH}:{settings.FRAME_HEIGHT}",
        "-q:v", str(settings.FRAME_QUALITY),
        "-f", "image2",
        "-strftime", "1",
        str(frame_pattern),
    ])

    return cmd
