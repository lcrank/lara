"""
WhatsApp Service - API Integration
Handles sending messages and downloading media from WhatsApp Cloud API
"""

import logging
import aiohttp
from typing import Optional
import io

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Manages communication with WhatsApp Cloud API"""
    
    BASE_URL = "https://graph.instagram.com/v18.0"
    
    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
    
    async def send_message(
        self,
        to: str,
        text: str,
        reply_to_message_id: Optional[str] = None
    ) -> bool:
        """
        Send a text message to a WhatsApp user
        
        Args:
            to: Recipient phone number (e.g., "+1234567890")
            text: Message text
            reply_to_message_id: Optional message ID to reply to
        
        Returns:
            True if message sent successfully
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": text
                }
            }
            
            if reply_to_message_id:
                payload["context"] = {"message_id": reply_to_message_id}
            
            url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"WhatsApp API error: {resp.status} - {error_text}")
                        return False
                    
                    result = await resp.json()
                    logger.info(f"Message sent to {to}: {result.get('messages', [{}])[0].get('id', 'unknown')}")
                    return True
        
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=e)
            return False
    
    async def send_media_message(
        self,
        to: str,
        media_type: str,  # "image", "video", "audio", "document"
        media_data: bytes,
        caption: Optional[str] = None
    ) -> bool:
        """
        Send media (image, screenshot, file) to WhatsApp user
        
        Args:
            to: Recipient phone number
            media_type: Type of media
            media_data: Binary media data
            caption: Optional caption for image/video
        
        Returns:
            True if sent successfully
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Upload media first
            upload_url = f"{self.BASE_URL}/{self.phone_number_id}/media"
            
            form_data = aiohttp.FormData()
            form_data.add_field('file', io.BytesIO(media_data), filename=f'media.{self._get_extension(media_type)}')
            form_data.add_field('type', media_type)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=form_data, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Media upload failed: {resp.status}")
                        return False
                    
                    upload_result = await resp.json()
                    media_id = upload_result.get('id')
                
                # Now send the media message
                message_url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
                
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": media_type,
                    media_type: {
                        "id": media_id
                    }
                }
                
                if caption and media_type in ["image", "video"]:
                    payload[media_type]["caption"] = caption
                
                async with session.post(message_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Message send failed: {resp.status}")
                        return False
                    
                    logger.info(f"Media message sent to {to}")
                    return True
        
        except Exception as e:
            logger.error(f"Error sending media: {str(e)}", exc_info=e)
            return False
    
    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Download media file from WhatsApp storage
        
        Args:
            media_id: ID of the media file
        
        Returns:
            Binary media data, or None if download fails
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Get media URL
            url = f"{self.BASE_URL}/{media_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to get media URL: {resp.status}")
                        return None
                    
                    info = await resp.json()
                    media_url = info.get('url')
                
                # Download the actual file
                async with session.get(media_url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download media: {resp.status}")
                        return None
                    
                    media_data = await resp.read()
                    logger.info(f"Downloaded media: {len(media_data)} bytes")
                    return media_data
        
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}", exc_info=e)
            return None
    
    @staticmethod
    def _get_extension(media_type: str) -> str:
        """Get file extension for media type"""
        extensions = {
            "image": "jpg",
            "video": "mp4",
            "audio": "ogg",
            "document": "pdf"
        }
        return extensions.get(media_type, "bin")
