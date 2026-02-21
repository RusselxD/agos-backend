from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import cloudinary
import cloudinary.uploader


class CloudinarySettings(BaseSettings):
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    CLOUDINARY_FOLDER: str = "agos/captured_frames"

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache()
def get_cloudinary_settings() -> CloudinarySettings:
    return CloudinarySettings()


cloudinary_settings: CloudinarySettings | None = None
cloudinary_enabled = False


def init_cloudinary():
    """
    Initialize the Cloudinary SDK with settings from environment variables.
    Call this at application startup.
    """
    global cloudinary_settings, cloudinary_enabled

    try:
        cloudinary_settings = get_cloudinary_settings()
        cloudinary.config(
            cloud_name=cloudinary_settings.CLOUDINARY_CLOUD_NAME,
            api_key=cloudinary_settings.CLOUDINARY_API_KEY,
            api_secret=cloudinary_settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        cloudinary_enabled = True
        print("✅ Cloudinary initialized")
    except Exception as e:
        cloudinary_enabled = False
        cloudinary_settings = None
        print(f"⚠️ Cloudinary init failed. Continuing without uploads: {e}")


async def upload_image(file: Any, filename: str, folder: str = None) -> dict | None:
    """
    Uploads an image (path or file-like object) to Cloudinary.
    
    Args:
        file: The local path to the file OR a file-like object.
        filename: The desired public ID (filename) in Cloudinary.
        folder: Optional subfolder. Defaults to settings.CLOUDINARY_FOLDER.
        
    Returns:
        A dictionary containing the 'secure_url' and 'public_id' or None on failure.
    """
    if not cloudinary_enabled or cloudinary_settings is None:
        print("⚠️ Cloudinary is not initialized. Skipping upload.")
        return None

    try:
        import asyncio
        from functools import partial
        
        loop = asyncio.get_running_loop()
        
        target_folder = folder or cloudinary_settings.CLOUDINARY_FOLDER
        
        upload_func = partial(
            cloudinary.uploader.upload,
            file,
            public_id=filename,
            folder=target_folder,
            overwrite=True,
            resource_type="image"
        )
        
        response = await loop.run_in_executor(None, upload_func)
        
        return {
            "secure_url": response.get("secure_url"),
            "public_id": response.get("public_id")
        }
        
    except Exception as e:
        print(f"❌ Cloudinary Upload Error: {e}")
        return None
