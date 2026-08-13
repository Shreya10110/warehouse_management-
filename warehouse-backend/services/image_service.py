import asyncio

import cloudinary
import cloudinary.uploader

from core.config import settings
from core.exceptions import AppError


async def upload_image(content: bytes, filename: str) -> str:
    """Upload image bytes to Cloudinary and return the secure delivery URL."""
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise AppError(503, "IMAGE_STORAGE_NOT_CONFIGURED", "Cloudinary credentials are not configured.")
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    result = await asyncio.to_thread(cloudinary.uploader.upload, content, folder="wms/damage", public_id=filename.rsplit(".", 1)[0])
    return result["secure_url"]
