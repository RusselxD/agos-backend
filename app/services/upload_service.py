from fastapi import File, UploadFile
import uuid
from app.core.cloudinary import upload_image


class UploadService():
    
    async def upload_responder_id_photo(self, file: UploadFile = File(...)):
        """
        Uploads a responder's ID photo directly to Cloudinary.
        """
        # 1. Generate a unique name
        unique_filename = f"responder_{uuid.uuid4()}"

        # 2. Upload the file object directly to Cloudinary
        # Cloudinary handles the file extension based on content
        result = await upload_image(
            file=file.file, 
            filename=unique_filename, 
            folder="agos/responder_ids"
        )

        if result and "secure_url" in result:
            return result["secure_url"]
        
        raise Exception("Failed to upload image to Cloudinary")


upload_service = UploadService()