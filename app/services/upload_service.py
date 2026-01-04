from fastapi import File, UploadFile
from pathlib import Path
import shutil
import uuid

RESPONDER_IDS_DIR = Path("app/storage/responder_ids")
RESPONDER_IDS_DIR.mkdir(parents=True, exist_ok=True)

class UploadService():
    
    async def upload_responder_id_photo(self, file: UploadFile = File(...)):

        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = RESPONDER_IDS_DIR / unique_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return file_path.as_posix()

upload_service = UploadService()