import os
import json
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

SYSTEM_PROMPT = """
You are a clinical note parser for a healthcare referral system.
Extract scheduling requirements from doctor notes and return ONLY valid JSON.
No explanation, no markdown, just the JSON object.

Return this exact format:
{
  "prereq_lab": "lab name or null",
  "timing": "timing instruction or null",
  "rx_action": "prescription action or null",
  "bundle_scheduling": true or false,
  "urgency": "routine or urgent"
}
"""

def parse_notes(notes_text):
    """Send clinical notes to GPT-4o and extract structured directives"""
    if not notes_text:
        return {
            "prereq_lab": None,
            "timing": None,
            "rx_action": None,
            "bundle_scheduling": False,
            "urgency": "routine"
        }

    client = _get_client()
    if client is None:
        return {
            "prereq_lab": None,
            "timing": None,
            "rx_action": None,
            "bundle_scheduling": False,
            "urgency": "routine"
        }

    response = client.chat.completions.create(
        model    = "gpt-4o",
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Parse these clinical notes:\n\n{notes_text}"}
        ],
        temperature = 0,
        max_tokens  = 200
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # If parsing fails, flag for human review — never act on bad output
        return {
            "prereq_lab": None,
            "timing": None,
            "rx_action": None,
            "bundle_scheduling": False,
            "urgency": "needs_review"
        }
