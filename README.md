# CareLoop
### Closing the loop — with CareLoop

CareLoop is a full-concierge referral fulfillment platform. The moment a doctor writes a referral, CareLoop reads the clinical notes with AI, pre-books the specialist, and texts the patient with everything arranged. Patient replies 1. Done.

---

## The problem
40% of specialist referrals in the US never become appointments. Patients are handed a name and a phone number and expected to navigate insurance, labs, prescriptions, and scheduling on their own. Most don't make it through.

## The solution
CareLoop intercepts the referral the moment it fires in the EHR, automates every coordination step, and removes all friction for the patient.

---

## Tech stack
- **Backend:** Python + Flask
- **AI:** Azure OpenAI GPT-4o (note parsing + barrier detection)
- **EHR integration:** FHIR R4 (ServiceRequest, Patient, DocumentReference, MedicationRequest, Task)
- **SMS:** Twilio
- **Transportation:** Uber Health API
- **Frontend demo:** Vanilla HTML/CSS/JS

---

## Project structure
```
careloop/
├── backend/
│   ├── app.py               # Main Flask server + webhooks
│   ├── fhir_client.py       # Reads EHR data via FHIR R4
│   ├── nlp_pipeline.py      # Azure OpenAI clinical note parser
│   ├── sms_service.py       # Twilio SMS handler
│   ├── barrier_detection.py # SDOH barrier detection + resolution
│   ├── network_query.py     # In-network specialist ranking engine
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html           # Interactive demo
```

---

## How to run locally

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill in your API keys
python app.py               # runs on http://localhost:5000
```

---

## API endpoints

| Method | Endpoint | What it does |
|--------|----------|-------------|
| POST | `/webhook/referral` | EHR fires this when a referral is written |
| POST | `/webhook/sms-reply` | Twilio fires this when patient replies |
| POST | `/jobs/check-no-response` | Cron job — checks for silent patients every hour |

---

## The full flow

1. Doctor writes referral → EHR fires `/webhook/referral`
2. CareLoop reads FHIR data — patient, notes, consent
3. Azure OpenAI parses clinical notes in under 3 seconds
4. Best available in-network specialist found and slot held
5. Patient gets one SMS — reply 1 to confirm everything
6. If no reply after 24h → barrier detection runs → specific fix applied
7. If specialist unavailable → network query finds next best in 8 seconds
8. PCP gets confirmation via FHIR Task resource — loop closed

---

## Built at SpinSci Hackathon 2025
