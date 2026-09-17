# NU Results

A modern, mobile-friendly and independent result viewer for National University, Bangladesh.

Production: `https://nu-results-bd.vercel.app/`

## What it does

NU Results provides dedicated result-search pages for:

- **Honours** — 1st, 2nd, 3rd, 4th Year and Consolidated Result
- **Degree Pass** — 1st, 2nd, 3rd Year and Consolidated Result
- **Master's** — Master's Final, Preliminary to Master's and ICT Course

The application retrieves result information from the National University result service and presents it in a responsive interface. It is an independent service, not the official National University website.

## Features

- National University CAPTCHA-based result workflow
- Short-lived encrypted server session for NU CSRF/cookie state
- Input validation and best-effort request rate limiting
- Dedicated result pages for each programme
- Student and course-wise result parsing
- Honours credit, letter-grade and calculated GPA summary
- Degree result status, course result and NU-supplied GPA when available
- Master's CGPA/GPA fields and supported course information
- Recent-search history stored locally in the browser
- Print / Save as PDF
- Web Share API with clipboard fallback
- Copy result text
- Responsive mobile, tablet and desktop UI
- Shared header, navigation and footer components
- SEO metadata, canonical URLs and structured WebSite data
- Static `robots.txt` and `sitemap.xml`
- Security response headers configured in Vercel

## Project structure

```text
nu-results/
├── api/
│   ├── index.py                 # Vercel/FastAPI entrypoint; shared app + Degree routes
│   ├── honours.py               # Honours result service, parser and routes
│   ├── degree.py                # Degree result parser and examination definitions
│   ├── masters.py               # Dedicated Master's serverless service
│   └── common/
│       ├── __init__.py
│       └── security.py          # Encrypted session, expiry and rate-limit helpers
│
├── public/
│   ├── index.html               # Refined homepage / result-category selector
│   ├── honours/index.html       # Honours result page
│   ├── degree/index.html        # Degree Pass result page
│   ├── masters/index.html       # Master's result page
│   ├── components/
│   │   ├── header.html          # Shared sticky header
│   │   ├── nav.html             # Shared result navigation
│   │   └── footer.html          # Shared footer
│   ├── assets/
│   │   ├── css/styles.css       # Shared stylesheet
│   │   └── js/
│   │       ├── core.js          # Shared shell + navigation loader
│   │       └── app.js           # Shared result UI and module-aware client logic
│   ├── about.html
│   ├── disclaimer.html
│   ├── grading.html
│   ├── how-to-use.html
│   ├── privacy.html
│   ├── robots.txt
│   ├── sitemap.xml
│   ├── favicon.svg
│   └── googled8f3621e34068255.html
│
├── tests/
│   ├── test_api.py              # Shared/Honours API regression tests
│   ├── test_degree.py            # Degree parser regression tests
│   └── test_masters.py           # Master's parser regression tests
│
├── .github/workflows/qa.yml     # CI syntax, test and structure checks
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── vercel.json
```

### Why there is an `api/index.py`

`api/index.py` is the Vercel/FastAPI entrypoint. It creates the shared FastAPI application and exposes the shared health/Degree API while including the Honours router. The module-specific parsers and result logic live in `api/honours.py`, `api/degree.py` and `api/masters.py`.

The root-level `degree.py`, `masters.py` compatibility shims and the three empty module-specific frontend JavaScript entrypoints are intentionally not part of the current structure because they duplicated existing canonical modules without adding result behavior.

## Frontend architecture

The site uses independent static result pages rather than a SPA router:

- `/` — choose a result category
- `/honours` — Honours search
- `/degree` — Degree Pass search
- `/masters` — Master's search

The header, navigation and footer are loaded from `public/components/`. The homepage intentionally does not load the global navigation bar to avoid duplicating the three result choices already shown on the homepage. The header remains sticky at the top.

All three result pages share `core.js` and `app.js`. Their `<body data-module="...">` value selects the appropriate API endpoints and result renderer, so separate one-line JavaScript entrypoint files are unnecessary.

## Backend architecture

### Honours

`api/honours.py` owns the Honours result workflow:

- Examination catalogue
- CAPTCHA/session retrieval
- Result request validation
- National University request handling
- HTML parsing
- Grade-point mapping
- Weighted GPA calculation

### Degree Pass

`api/degree.py` owns the Degree examination catalogue and result parser. Degree API endpoints remain on the shared FastAPI entrypoint in `api/index.py` so the existing production endpoint contract is preserved.

### Master's

`api/masters.py` is an independent Vercel/FastAPI service for the Master's result system. It supports Master's Final, Preliminary to Master's and ICT Course searches and maintains a module-specific encrypted session marker.

## Security

- The application uses the National University CAPTCHA flow; it does not bypass CAPTCHA.
- NU CSRF tokens and cookies are sealed into a short-lived encrypted session token.
- The session expires after five minutes.
- Basic request rate limiting is applied on result/CAPTCHA operations.
- The browser receives the encrypted session token rather than raw NU cookies or CSRF state.
- Vercel config adds security response headers.

Because the application runs in a serverless environment, rate limiting is best-effort and is not a replacement for a shared distributed rate-limit store if traffic becomes large.

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

The GitHub Actions workflow checks Python syntax, JavaScript syntax, backend tests and required project files.

Run the same checks locally:

```bash
python -m py_compile api/index.py api/honours.py api/degree.py api/masters.py api/common/security.py
node --check public/assets/js/core.js
node --check public/assets/js/app.js
SESSION_SIGNING_SECRET="ci-test-secret" python -m unittest discover -s tests -p 'test_*.py'
```

## Deployment

The project is designed for Vercel.

Set this environment variable in Vercel:

```text
SESSION_SIGNING_SECRET=<long-random-secret>
```

Never commit the secret to GitHub.

`vercel.json` configures the Python functions, cache behavior and security headers. The Master's service is configured as its own Python function with a 30-second maximum duration.

## SEO and public pages

The public site includes:

- `/robots.txt`
- `/sitemap.xml`
- `/how-to-use.html`
- `/grading.html`
- `/about.html`
- `/privacy.html`
- `/disclaimer.html`

The homepage and result pages contain canonical URLs and page-specific metadata. `robots.txt` and `sitemap.xml` are static public files, so there is no duplicate FastAPI implementation for those endpoints.

## Responsible use

This project is intended for individual result lookups. Do not use it for bulk collection, CAPTCHA bypass, access-control circumvention or excessive automated requests. Use the official National University result portal for final verification of important academic information.

## Disclaimer

NU Results is an independent project and is not the official website of National University, Bangladesh. Result information is retrieved from the National University result service and should be verified through the official portal when required.
