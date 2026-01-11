import asyncio
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Set
from app.crud.model_readings import model_readings as model_readings_crud
from app.schemas import ModelReadingCreate
from app.core.database import AsyncSessionLocal
from app.services.websocket_service import websocket_service
from app.models.data_sources.model_readings import ModelReadings
from app.schemas import ModelWebSocketResponse
from app.core.state import fusion_state_manager
from app.schemas import BlockageStatus

from app.core.config import settings

class MLService:
    """
    Service responsible for running Machine Learning inference on captured video frames.
    
    Architecture Role: "The Brain"
    - Input: Watches the 'captured_frames' directory for new .jpg files created by FFmpeg.
    - Process: Simulates running a classification model (e.g., TensorFlow/PyTorch).
    - Output: Produces a classification result (Clear/Partial/Blocked) for the DB and WebSockets.
    """

    def __init__(self):
        self.is_running = False
        self.frames_dir = Path(settings.FRAMES_OUTPUT_DIR)
        
        # Memory set to track which files we have already analyzed.
        self.processed_files: Set[Path] = set()
        self.last_processed_time: datetime = None

    async def start(self):
        """
        Start the background analysis loop.
        Call this when the application starts (e.g., in main.py lifespan).
        """
        if self.is_running:
            return
        
        # 1. Handle existing files
        if self.frames_dir.exists():
            all_frames = sorted(self.frames_dir.glob("frame_*.jpg"), reverse=True)
            
            if all_frames:
                # Process only the SINGLE most recent frame found on disk
                latest_existing = all_frames[0]
                print(f"🧠 ML Service: Processing latest existing frame: {latest_existing.name}")
                await self._process_frame(latest_existing)
                
                # Mark ALL currently existing files as 'processed' so the loop ignores them
                self.processed_files = set(all_frames)
        
        self.is_running = True
        print(f"✅ ML Service started. Ignored {len(self.processed_files)} old frames. Watching for new ones...")
        asyncio.create_task(self._analysis_loop())

    async def stop(self):
        """Stop the background analysis loop."""
        self.is_running = False
        print("✅ ML Service stopping...")

    async def _analysis_loop(self):
        """
        The heartbeat of the ML service.
        Periodically checks the disk for new images to analyze.
        """
        while self.is_running:
            try:
                # 1. DISCOVERY: Look for all current .jpg files
                if not self.frames_dir.exists():
                    await asyncio.sleep(5)
                    continue

                current_files = set(self.frames_dir.glob("frame_*.jpg"))
                
                # 2. FILTER: Find files we haven't seen before
                new_files = sorted(list(current_files - self.processed_files))
                
                # 3. PROCESS: Run inference ONLY on the newest file if many appeared
                if new_files:
                    latest_file = new_files[-1]
                    
                    # Rate limiting check: Strict Cool-down
                    now = datetime.now(timezone.utc)
                    should_process = True
                    
                    if self.last_processed_time:
                        elapsed = (now - self.last_processed_time).total_seconds()
                        # Strict check: Ensure at least ~115s have passed (5s buffer for jitter)
                        if elapsed < settings.FRAME_CAPTURE_INTERVAL_SECONDS - 5:
                            should_process = False

                    if should_process:
                        await self._process_frame(latest_file)
                        self.last_processed_time = now
                    
                    # Mark all discovered files as processed so we don't look at them again
                    # This prevents the loop from re-evaluating the same 100 files every cycle
                    self.processed_files.update(current_files)
                
                # 4. CLEANUP: Keep memory clean (only track what's actually on disk)
                self.processed_files = self.processed_files.intersection(current_files)
                
                # Poll every 10 seconds - responsive enough, but not busy-waiting
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"Error in ML loop: {e}")
                await asyncio.sleep(5)

    async def _process_frame(self, file_path: Path):
        """
        Simulate running an AI model on a single image.
        """
        try:
            # Simulate a model prediction
            prediction = random.choices(["clear", "partial", "blocked"], weights=[0.7, 0.2, 0.1], k=1)[0]
            percentage = round(random.uniform(0.75, 0.99), 2)
            debris_count = random.randint(0, 20)

            # print(f"🔍 ML Result: {prediction[0].upper() + prediction[1:]} ({int(percentage*100)}%)")
            print(f"🔍 ML Result: {prediction.capitalize()} ({int(percentage*100)}%), Debris Count: {debris_count}")

            # Store the result in the database
            async with AsyncSessionLocal() as db:
                obj_in = ModelReadingCreate(
                    camera_device_id=1,
                    image_path=str(file_path),
                    timestamp=datetime.now(timezone.utc),
                    blockage_percentage=percentage * 100,
                    blockage_status=prediction,
                    total_debris_count=debris_count
                )
                db_obj: ModelReadings = await model_readings_crud.create_and_return(db=db, obj_in=obj_in)

            # Broadcast the new prediction via WebSockets
            blockage_reading = ModelWebSocketResponse(
                status="success", 
                message="Retrieved successfully",
                blockage_status = prediction
            )

            await websocket_service.broadcast_update(
                update_type="blockage_detection_update", 
                data=blockage_reading.model_dump(mode='json'),
                location_id=1
            )

            # Update fusion analysis state
            await fusion_state_manager.recalculate_visual_status_score(
                blockage_status=BlockageStatus(
                    status=prediction,
                    timestamp=db_obj.timestamp
                ), 
                location_id=1
            )

        except Exception as e:
            print(f"Failed to analyze frame {file_path}: {e}")

# Global instance
ml_service = MLService()
