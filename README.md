# NU Results

A modern web-based result viewer for National University, Bangladesh.

## Current status

- Honours 4th Year result lookup is implemented.
- Uses the official public NU result form as the upstream source.
- CAPTCHA is solved by the user; no CAPTCHA bypass is implemented.
- Result HTML is parsed into structured JSON before rendering.

## Stack

- Python + FastAPI
- Requests
- BeautifulSoup
- HTML/CSS/JavaScript frontend
- Vercel deployment

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Open `http://127.0.0.1:8000/`.

## Vercel

Set the environment variable `SESSION_SIGNING_SECRET` to a long random value before production deployment. The API endpoint is under `/api` and the frontend is served from `public/`.

## Responsible use

This project is intended for individual result lookups. It should not be used for bulk collection, CAPTCHA bypass, access-control circumvention, or excessive automated requests. Production use should comply with National University policies and applicable law.

## Disclaimer

This is an independent project and is not an official National University website. Important academic information should be verified through the official NU result portal.
