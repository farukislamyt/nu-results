# NU Results

A modern, mobile-first and independent result-viewing interface for National University, Bangladesh.

## Features

- Honours 1st, 2nd, 3rd and 4th Year lookup
- Honours Consolidated Result option
- Official NU CAPTCHA workflow; no CAPTCHA bypass
- Encrypted, short-lived server session for NU cookies/CSRF state
- Input validation and best-effort request rate limiting
- Structured student and course-wise result parsing
- Credit and letter-grade display
- Calculated GPA summary when returned course data supports it
- Professional responsive UI for mobile, tablet and desktop
- Loading, success and error states
- Print / Save as PDF with a print-optimized result sheet
- Web Share API with clipboard fallback
- Copy result text
- Local-only recent-search history (up to five entries)
- SEO-ready metadata, canonical links and structured WebSite data
- Crawl controls through dynamic `robots.txt` and `sitemap.xml`
- How-to-use, grading, about, privacy and disclaimer pages
- Security response headers on Vercel

## Project structure

```text
nu-results/
├── api/
│   └── index.py                 # FastAPI API + clean public page routes
├── public/
│   ├── index.html               # Main result search UI
│   ├── pages/                   # Public informational pages
│   │   ├── about.html
│   │   ├── disclaimer.html
│   │   ├── grading.html
│   │   ├── how-to-use.html
│   │   └── privacy.html
│   └── assets/
│       ├── css/
│       │   └── styles.css
│       ├── js/
│       │   └── app.js
│       └── images/
├── tests/
│   └── test_api.py              # Backend regression tests
├── .github/
│   └── workflows/
│       └── qa.yml               # Automated syntax, tests and structure checks
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── vercel.json
```

Clean public URLs such as `/about.html` are preserved even though informational page files live under `public/pages/`. The FastAPI routes and Vercel rewrites keep local and production URL behavior aligned.

## Stack

- Python + FastAPI
- Requests
- BeautifulSoup
- Cryptography / Fernet for temporary encrypted session state
- HTML/CSS/JavaScript frontend
- Vercel-compatible serverless deployment

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SESSION_SIGNING_SECRET="replace-with-a-new-random-secret"
uvicorn api.index:app --reload
```

Open `http://127.0.0.1:8000/`.

## Quality checks

Run the same core checks used by GitHub Actions locally:

```bash
python -m py_compile api/index.py
node --check public/assets/js/app.js
SESSION_SIGNING_SECRET="ci-test-secret" python -m unittest discover -s tests -p 'test_*.py'
```

## SEO endpoints

- `/robots.txt` is generated dynamically from the current host.
- `/sitemap.xml` lists only public pages intended for indexing.
- `/api/` is excluded from crawling.

The production domain should be added to Google Search Console and Bing Webmaster Tools after deployment. Search engines may take time to crawl and index pages; indexing is not guaranteed.

## Vercel

Create `SESSION_SIGNING_SECRET` as a Vercel environment variable using a new, long random value. Never commit the secret to GitHub and never reuse a secret exposed in chat, logs or source control.

The API is under `/api`; the main UI is `public/index.html`; assets are under `public/assets`; informational source files are under `public/pages`; clean informational URLs are handled by the application and Vercel rewrites.

## Security notes

The temporary NU session is encrypted and expires after five minutes. The browser receives only the encrypted session token. Rate limiting is conservative and best-effort because serverless instances are stateless; a shared rate-limit store can be considered if traffic grows.

## Responsible use

This project is intended for individual result lookups. It should not be used for bulk collection, CAPTCHA bypass, access-control circumvention, or excessive automated requests. Production use should comply with National University policies and applicable law.

## Disclaimer

This is an independent project and is not an official National University website. Important academic information should be verified through the official NU result portal.
