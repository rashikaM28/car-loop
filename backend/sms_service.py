import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM  = os.getenv("TWILIO_PHONE_NUMBER", "+18005551234")

client = Client(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None

def send_sms(to_phone, message):
    """Send an SMS via Twilio"""
    if client is None:
        print(f"[LOCAL MODE] SMS to {to_phone}: {message}")
        return "local-mode"

    try:
        msg = client.messages.create(
            body = message,
            from_= TWILIO_FROM,
            to   = to_phone
        )
        print(f"SMS sent to {to_phone} — SID: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"SMS failed to {to_phone}: {e}")
        return None
