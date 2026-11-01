import os
import requests
from dotenv import load_dotenv

# Force load .env from root directory
load_dotenv()

def send_whatsapp_audio(phone_number: str, audio_bytes: bytes, text_caption: str) -> bool:
    """
    Uploads audio buffer and sends audio message via Meta WhatsApp Cloud API.
    """
    # Try fetching from environment first, fallback to loading .env directly
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID")

    # Debug printer (check terminal to see exact loaded state)
    if not token or not phone_id:
        print(f"⚠️ Credentials missing in python: TOKEN={bool(token)}, PHONE_ID={bool(phone_id)}")
        return False

    # Clean phone number (strip spaces, dashes, + sign for Meta API payload)
    clean_phone = "".join(filter(str.isdigit, phone_number))

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Step A: Upload audio buffer to Meta media endpoint
        upload_url = f"https://graph.facebook.com/v18.0/{phone_id}/media"
        files = {
            "file": ("advisory.mp3", audio_bytes, "audio/mp3"),
            "messaging_product": (None, "whatsapp")
        }
        upload_res = requests.post(upload_url, headers=headers, files=files)
        media_id = upload_res.json().get("id")

        if not media_id:
            print(f"❌ Failed to upload media to WhatsApp: {upload_res.text}")
            return False

        # Step B: Send WhatsApp Audio message to recipient
        message_url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "audio",
            "audio": {"id": media_id}
        }
        msg_res = requests.post(message_url, headers=headers, json=payload)
        
        if msg_res.status_code in [200, 201]:
            return True
        else:
            print(f"❌ WhatsApp Message Send Failed: {msg_res.text}")
            return False

    except Exception as e:
        print(f"❌ WhatsApp Dispatch Exception: {e}")
        return False