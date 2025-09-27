
# AI Mental Health Friend - Demo

This is a demo, multilingual, self-contained prototype of the "AI Mental Health Friend".

## What it includes
- Frontend: simple HTML/CSS/JS single-page app (in `frontend/`)
- Backend: Flask app (in `backend/app.py`) with SQLite DB (demo)
- Clinician content: `content/clinician_content.json`
- Basic crisis detection via multilingual keyword rules.
- Mood tracker, CBT short worksheet flow, and breathing exercise guidance.
- Export and delete endpoints for basic privacy flow.

## Requirements (to run locally)
- Python 3.8+
- Install dependencies:
```
pip install flask
```

## Run
1. From project root:
```
cd backend
python app.py
```
2. Open browser to `http://localhost:8000`

## Notes & Limitations
- This is a demo. The "encryption" used for some fields is base64 NOT secure — replace with real encryption and key management for production.
- No real LLM is used. Replies are templated clinician content. For production, integrate a multilingual LLM and robust safety layers.
- Crisis detection is rule-based; tune and test heavily before any public use.
- Clinician review and legal/ethical compliance required before live deployment.

