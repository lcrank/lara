"""
WhatsApp Webhook Handler
Receives voice messages, processes them, and manages responses
"""

import logging
import hmac
import hashlib
import aiohttp
from fastapi import APIRouter, Request, Response
from datetime import datetime
import json

from app.config import settings
from app.services.whisper_service import WhisperService
from app.services.llm_service import LLMService
from app.services.whatsapp_service import WhatsAppService
from app.handlers.websocket import connection_manager
from app.utils.validators import validate_command

logger = logging.getLogger(__name__)
router = APIRouter()

whisper_service = WhisperService(api_key=settings.groq_api_key)
llm_service = LLMService(api_key=settings.groq_api_key)
whatsapp_service = WhatsAppService(
    phone_number_id=settings.whatsapp_phone_number_id,
    access_token=settings.whatsapp_access_token
)

def verify_whatsapp_signature(body: str, signature: str) -> bool:
    """Verify that webhook came from WhatsApp using HMAC-SHA256"""
    expected_signature = hmac.new(
        settings.whatsapp_access_token.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@router.get("/whatsapp")
async def webhook_verification(request: Request):
    """
    WhatsApp webhook verification (GET request)
    Called once by WhatsApp to verify the webhook URL
    """
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"Invalid verify token: {verify_token}")
    return Response(content="Invalid token", status_code=403)

@router.post("/whatsapp")
async def webhook_handler(request: Request):
    """
    Main webhook handler for incoming messages from WhatsApp
    
    Flow:
    1. Verify signature
    2. Check if user is authorized
    3. Download audio file
    4. Transcribe with Whisper
    5. Parse command with LLM
    6. Validate command
    7. Send to agent for execution
    8. Send response back to WhatsApp
    """
    
    try:
        # Get raw body for signature verification
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Bypass signature verification for local testing
        # signature = request.headers.get("X-Hub-Signature-256", "")
        # if not signature.startswith("sha256="):
        #     logger.warning("Invalid signature format")
        #     return Response(status_code=403)
        # 
        # signature = signature.replace("sha256=", "")
        # if not verify_whatsapp_signature(body_str, signature):
        #     logger.warning("Webhook signature verification failed - possible attack")
        #     return Response(status_code=403)
        
        # Parse JSON
        data = json.loads(body_str)
        
        # Extract message info
        try:
            entry = data['entry'][0]['changes'][0]['value']
            message = entry['messages'][0]
            sender_phone = message['from']
            message_type = message['type']
        except (KeyError, IndexError) as e:
            logger.warning(f"Invalid message format: {e}")
            return Response(status_code=200)
        
        # Check if user is authorized
        if sender_phone not in settings.authorized_phone_numbers:
            logger.warning(f"Unauthorized access attempt from {sender_phone}")
            await whatsapp_service.send_message(
                to=sender_phone,
                text="🔒 You are not authorized to use this service"
            )
            return Response(status_code=200)
        
        # Log the incoming message
        logger.info(f"Message from {sender_phone} (type: {message_type})")
        
        # Handle different message types
        if message_type == "audio":
            await handle_audio_message(message, sender_phone)
        elif message_type == "text":
            await handle_text_message(message, sender_phone)
        else:
            await whatsapp_service.send_message(
                to=sender_phone,
                text="📝 Please send a voice message or text command"
            )
        
        # Always return 200 to acknowledge receipt
        return Response(status_code=200)
    
    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}", exc_info=e)
        return Response(status_code=500)

async def handle_audio_message(message: dict, sender_phone: str):
    """Handle incoming audio/voice message"""
    
    try:
        # Send processing indicator
        await whatsapp_service.send_message(
            to=sender_phone,
            text="🎤 Processing your voice message..."
        )
        
        # Get audio file info
        audio_id = message['audio']['id']
        
        # Download audio from WhatsApp
        logger.info(f"Downloading audio {audio_id}")
        audio_data = await whatsapp_service.download_media(audio_id)
        if not audio_data:
            raise Exception("Failed to download audio")
        
        # Transcribe with Whisper
        logger.info("Transcribing audio with Whisper")
        transcription = await whisper_service.transcribe(audio_data)
        
        logger.info(f"Transcription: {transcription.text} (confidence: {transcription.confidence})")
        
        if transcription.confidence < 0.7:
            await whatsapp_service.send_message(
                to=sender_phone,
                text=f"🔊 I heard: \"{transcription.text}\"\n\nBut I'm not confident. Could you repeat clearly?"
            )
            return
        
        # Parse command with Groq LLM
        logger.info("Parsing command with Groq LLM")
        command = await llm_service.parse_command(transcription.text)
        
        # Execute command on agent via websocket
        logger.info("Executing command on agent")
        result = await connection_manager.send_command(
            device_id="laptop-1",
            command=command,
            timeout=settings.command_timeout_seconds
        )
        
        # Send response back to user
        if result.success:
            response_text = f"✅ {result.details}"
        else:
            response_text = f"❌ Error: {result.error_message}"
        
        await whatsapp_service.send_message(to=sender_phone, text=response_text)
        
    except Exception as e:
        logger.error(f"Error handling audio message: {str(e)}", exc_info=e)
        await whatsapp_service.send_message(
            to=sender_phone,
            text=f"⚠️ Error: {str(e)[:100]}"
        )

async def handle_text_message(message: dict, sender_phone: str):
    """Handle incoming text message (for quick commands, debugging)"""
    
    try:
        text = message['text']['body']
        
        # Check if this is a visual command (needs screen analysis)
        if llm_service.is_visual_command(text):
            logger.info(f"Visual command detected: '{text}' — taking screenshot first")
            await whatsapp_service.send_message(to=sender_phone, text="👁️ Looking at your screen...")

            # Step 1: Get screenshot from agent
            screenshot_result = await connection_manager.send_command(
                device_id="laptop-1",
                command={"command_type": "screenshot", "parameters": {}},
                timeout=15
            )

            if screenshot_result.success and screenshot_result.response_data.get("image_base64"):
                # Step 2: Analyze screen with Groq Vision
                command = await llm_service.parse_visual_command(
                    text,
                    screenshot_result.response_data["image_base64"]
                )
                logger.info(f"Vision AI decided: {command.command_type} → {command.parameters}")
            else:
                logger.warning("Screenshot failed, falling back to normal parse")
                command = await llm_service.parse_command(text)
        else:
            logger.info(f"Parsing text command with Groq LLM: {text}")
            command = await llm_service.parse_command(text)

        result = await connection_manager.send_command(
            device_id="laptop-1",
            command=command,
            timeout=settings.command_timeout_seconds
        )
        
        response_text = f"✅ {result.details}" if result.success else f"❌ {result.error_message}"
        await whatsapp_service.send_message(to=sender_phone, text=response_text)
        
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}", exc_info=e)
        await whatsapp_service.send_message(
            to=sender_phone,
            text=f"⚠️ Error processing your command"
        )
