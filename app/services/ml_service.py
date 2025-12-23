import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import  Set
from app.crud.model_readings import model_readings as model_readings_crud
from app.schemas import ModelReadingCreate
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.core.database import AsyncSessionLocal
from app.core.ws_manager import ws_manager

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
        print(f"🧠 ML Service started. Ignored {len(self.processed_files)} old frames. Watching for new ones...")
        asyncio.create_task(self._analysis_loop())

    async def stop(self):
        """Stop the background analysis loop."""
        self.is_running = False
        print("🧠 ML Service stopping...")

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
                new_files = current_files - self.processed_files
                
                # 3. PROCESS: Run inference on new files
                for file_path in new_files:
                    await self._process_frame(file_path)
                    self.processed_files.add(file_path)
                
                # 4. CLEANUP: Keep memory clean
                self.processed_files = self.processed_files.intersection(current_files)
                
                await asyncio.sleep(2)
                
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
            confidence = round(random.uniform(0.75, 0.99), 2)
            
            print(f"🔍 ML Result: {prediction[0].upper() + prediction[1:]} ({int(confidence*100)}%)")
            
            async with AsyncSessionLocal() as db:
                obj_in = ModelReadingCreate(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status=prediction, 
                    confidence=confidence,
                    image_path=str(file_path)
                )
                await model_readings_crud.create(db=db, obj_in=obj_in)

            await ws_manager.broadcast({
                "type": "blockage_detection_update",
                "data": {"status": prediction}
            })
            
        except Exception as e:
            print(f"Failed to analyze frame {file_path}: {e}")

# Global instance
ml_service = MLService()
