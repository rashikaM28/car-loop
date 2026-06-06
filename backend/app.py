from flask import Flask, request, jsonify
from flask_cors import CORS
from fhir_client import get_referral, get_patient, get_clinical_notes
from nlp_pipeline import parse_notes
from sms_service import send_sms
from barrier_detection import detect_barrier, resolve_barrier
from network_query import find_specialists

app = Flask(__name__)
CORS(app)

# ── Webhook: EHR fires this the moment a referral is written ──────────────────
@app.route("/webhook/referral", methods=["POST"])
def handle_referral():
    data = request.json
    referral_id = data.get("referral_id")
    patient_id  = data.get("patient_id")

    # 1. Pull referral + patient from EHR via FHIR
    referral = get_referral(referral_id)
    patient  = get_patient(patient_id)

    # 2. Check consent — never text without it
    if not patient.get("sms_consent"):
        return jsonify({"status": "skipped", "reason": "no consent"}), 200

    # 3. Read doctor's clinical notes and extract what's needed
    notes    = get_clinical_notes(patient_id)
    parsed   = parse_notes(notes)
    # parsed = { prereq_lab, timing, rx_action, bundle_scheduling }

    # 4. Find best available specialist
    specialist = find_specialists(
        specialty     = referral["specialty"],
        insurance     = patient["insurance"],
        zip_code      = patient["zip_code"],
        preferred_id  = referral.get("preferred_specialist_id")
    )

    if not specialist:
        return jsonify({"status": "error", "reason": "no specialist found"}), 500

    # 5. Text the patient — everything already arranged
    phone   = patient["phone"]
    name    = patient["first_name"]
    message = (
        f"Hi {name}! Dr. {referral['pcp_name']} referred you to {referral['specialty']}. "
        f"We've reserved a slot with {specialist['name']} on {specialist['available_date']}. "
        f"Reply 1 to confirm, 2 for a different time. Reply STOP to opt out."
    )
    send_sms(phone, message)

    return jsonify({"status": "outreach_sent", "specialist": specialist["name"]}), 200


# ── Webhook: Patient replies to the SMS ───────────────────────────────────────
@app.route("/webhook/sms-reply", methods=["POST"])
def handle_sms_reply():
    phone   = request.json.get("phone")
    message = request.json.get("message", "").strip().lower()

    if message == "1":
        send_sms(phone, "All confirmed! We'll send you a reminder 24 hours before. See you soon!")
        return jsonify({"status": "confirmed"}), 200

    elif message == "stop":
        send_sms(phone, "You've been opted out. Call (800) 555-1234 to manage your referral directly.")
        return jsonify({"status": "opted_out"}), 200

    elif message == "2":
        send_sms(phone, "No problem — here are 3 other available times. Reply 1, 2, or 3 to pick one:\n1. Monday June 24 at 10am\n2. Tuesday June 25 at 2pm\n3. Wednesday June 26 at 9am")
        return jsonify({"status": "rescheduling"}), 200

    else:
        # Unknown reply — run barrier detection on it
        barrier = detect_barrier(message=message)
        response_message = resolve_barrier(barrier, phone)
        send_sms(phone, response_message)
        return jsonify({"status": "barrier_handled", "barrier": barrier}), 200


# ── Scheduled job: Check for no responses after 24h ──────────────────────────
@app.route("/jobs/check-no-response", methods=["POST"])
def check_no_response():
    # In production this runs on a cron job every hour
    # For the hackathon we just expose it as an endpoint
    patients_no_response = request.json.get("patients", [])

    for patient in patients_no_response:
        barrier = detect_barrier(
            zip_code   = patient.get("zip_code"),
            prior_notes= patient.get("prior_notes"),
            hours_silent=patient.get("hours_silent", 24)
        )
        message = resolve_barrier(barrier, patient["phone"])
        send_sms(patient["phone"], message)

    return jsonify({"status": "processed", "count": len(patients_no_response)}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
