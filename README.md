# NU Results

A modern, mobile-friendly result viewer for National University, Bangladesh.

## Current features

- Honours 1st, 2nd, 3rd and 4th Year lookup
- Honours Consolidated Result option
- Official NU CAPTCHA workflow; no CAPTCHA bypass
- Encrypted, short-lived server session for NU cookies/CSRF state
- Input validation and best-effort request rate limiting
- Structured student and course-wise result parsing
- Credit and letter-grade display
- Calculated GPA summary when the returned course data supports it
- Print / Save as PDF through the browser print dialog
- Web Share API with clipboard fallback
- Copy result text
- Local-only recent-search history (up to five entries)
- Mobile-first responsive UI
- Result checking guide, grading reference and privacy pages

## Stack

- Python + FastAPI
- Requests
- BeautifulSoup
- Cryptography / Fernet for temporary encrypted session state
- HTML/CSS/JavaScript frontend
- Vercel deployment

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SESSION_SIGNING_SECRET="replace-with-a-new-random-secret"
uvicorn api.index:app --reload
```

Open `http://127.0.0.1:8000/`.

## Vercel

Create the environment variable `SESSION_SIGNING_SECRET` with a long random value. Do not commit the secret to GitHub and do not reuse a secret that has been exposed in chat, logs or source control.

The API is under `/api`, while the frontend is served from `public/`.

## Security notes

The temporary NU session is encrypted and expires after five minutes. The browser only receives the encrypted session token. Rate limiting is intentionally conservative and is best-effort because Vercel serverless instances are stateless; a shared rate-limit store can be added later if traffic grows.

## Responsible use

This project is intended for individual result lookups. It should not be used for bulk collection, CAPTCHA bypass, access-control circumvention, or excessive automated requests. Production use should comply with National University policies and applicable law.

## Disclaimer

This is an independent project and is not an official National University website. Important academic information should be verified through the official NU result portal.
