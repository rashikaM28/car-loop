import os
import requests
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def _get_client():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        return None
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-02-01"
    )

# Low transit score zip codes (in production pull from a real transit API)
LOW_TRANSIT_ZIPS = {"73301", "73344", "75001", "75002"}

BARRIER_RESPONSES = {
    "transportation": (
        "We noticed getting there might be tricky. "
        "We've arranged a free ride for your appointment. Reply 1 to confirm and your ride will be set."
    ),
    "cost": (
        "Cost should never be a barrier to care. "
        "We've connected you with our financial counselor — someone will call within 2 hours. Your slot is held."
    ),
    "language": (
        "Hola! Podemos ayudarte en español. "
        "Tu cita está lista — responde 1 para confirmar."
    ),
    "scheduling": (
        "No problem — here are 3 other available times:\n"
        "1. Monday at 10am\n2. Tuesday at 2pm\n3. Wednesday at 9am\n"
        "Reply 1, 2, or 3 to pick one."
    ),
    "unknown": (
        "We want to make sure you get the care you need. "
        "A care coordinator will call you within 24 hours to help."
    )
}

def detect_barrier(message=None, zip_code=None, prior_notes=None, hours_silent=0):
    """
    Figure out WHY a patient isn't responding.
    Uses zip code transit data, prior notes, and any reply text.
    """

    # 1. Cost barrier — patient explicitly said something
    if message:
        cost_keywords = ["afford", "cost", "expensive", "money", "pay", "insurance"]
        if any(word in message.lower() for word in cost_keywords):
            return "cost"

        # Language barrier — non-English reply
        if not _is_english(message):
            return "language"

        # Scheduling conflict
        schedule_keywords = ["can't", "busy", "different", "another", "reschedule", "time"]
        if any(word in message.lower() for word in schedule_keywords):
            return "scheduling"

    # 2. Transportation barrier — zip code signal
    if zip_code and zip_code in LOW_TRANSIT_ZIPS:
        return "transportation"

    # 3. Transportation barrier — prior notes mention it
    if prior_notes:
        transport_keywords = ["no vehicle", "no car", "no transportation", "bus", "relies on"]
        if any(kw in prior_notes.lower() for kw in transport_keywords):
            return "transportation"

    # 4. Silent for 72+ hours — escalate to human
    if hours_silent >= 72:
        return "unknown"

    return "unknown"

def resolve_barrier(barrier_type, phone=None):
    """Return the right message for the detected barrier"""
    return BARRIER_RESPONSES.get(barrier_type, BARRIER_RESPONSES["unknown"])

def _is_english(text):
    """Simple check — in production use a language detection library"""
    client = _get_client()
    if client is None:
        return True

    try:
        response = client.chat.completions.create(
            model    = "gpt-4o",
            messages = [
                {"role": "system", "content": "Reply with only 'english' or 'other'."},
                {"role": "user",   "content": f"What language is this: {text}"}
            ],
            max_tokens  = 5,
            temperature = 0
        )
        return response.choices[0].message.content.strip().lower() == "english"
    except:
        return True
