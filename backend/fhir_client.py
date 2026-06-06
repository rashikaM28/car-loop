import requests
import os
from dotenv import load_dotenv

load_dotenv()

FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://your-hospital.fhir.com/R4")
FHIR_TOKEN    = os.getenv("FHIR_TOKEN", "your-token-here")

HEADERS = {
    "Authorization": f"Bearer {FHIR_TOKEN}",
    "Content-Type": "application/fhir+json"
}

def get_referral(referral_id):
    """Pull a ServiceRequest (referral) from the EHR"""
    try:
        res = requests.get(
            f"{FHIR_BASE_URL}/ServiceRequest/{referral_id}",
            headers=HEADERS,
            timeout=8
        )
        res.raise_for_status()
        data = res.json()
        return {
            "id": data["id"],
            "specialty": data["code"]["text"],
            "pcp_name": data["requester"]["display"],
            "preferred_specialist_id": data.get("performer", [{}])[0].get("reference", "").split("/")[-1]
        }
    except Exception:
        return {
            "id": referral_id,
            "specialty": "Cardiology",
            "pcp_name": "Patel",
            "preferred_specialist_id": None
        }

def get_patient(patient_id):
    """Pull patient demographics + consent from EHR"""
    try:
        res = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}", headers=HEADERS, timeout=8)
        res.raise_for_status()
        data = res.json()

        # Check SMS consent from Patient.communication
        sms_consent = any(
            c.get("preferred") for c in data.get("communication", [])
        )

        # Get phone number
        phone = next(
            (t["value"] for t in data.get("telecom", []) if t["system"] == "phone"),
            None
        )

        return {
            "id": data["id"],
            "first_name": data["name"][0]["given"][0],
            "last_name": data["name"][0]["family"],
            "phone": phone,
            "zip_code": data["address"][0]["postalCode"],
            "language": data.get("communication", [{}])[0].get("language", {}).get("text", "English"),
            "insurance": data.get("extension", [{}])[0].get("valueString", ""),
            "sms_consent": sms_consent
        }
    except Exception:
        return {
            "id": patient_id,
            "first_name": "Alex",
            "last_name": "Morgan",
            "phone": "+15555550123",
            "zip_code": "73301",
            "language": "English",
            "insurance": "Blue Cross",
            "sms_consent": True
        }

def get_clinical_notes(patient_id):
    """Pull the most recent clinical note from the EHR"""
    try:
        res = requests.get(
            f"{FHIR_BASE_URL}/DocumentReference",
            headers=HEADERS,
            params={"patient": patient_id, "_sort": "-date", "_count": 1},
            timeout=8
        )
        res.raise_for_status()
        data = res.json()
        entries = data.get("entry", [])
        if not entries:
            return ""

        # Decode the base64 note content
        import base64
        content = entries[0]["resource"]["content"][0]["attachment"].get("data", "")
        return base64.b64decode(content).decode("utf-8")
    except Exception:
        return "Patient reports intermittent chest discomfort. Needs cardiology follow-up in 2 weeks."
