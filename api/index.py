import hashlib
import os
import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="NU Results API", version="2.1.0")
# The frontend is served by this same application, so cross-origin access is unnecessary.
app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Accept"])

NU_URL = "https://results.nu.ac.bd/honours"
SESSION_TTL = 5 * 60
RATE_WINDOW = 60
RATE_LIMIT = 20
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
PAGES_DIR = os.path.join(PUBLIC_DIR, "pages")
_rate_cache: dict[str, list[float]] = {}


def session_key() -> bytes:
    configured = os.environ.get("SESSION_SIGNING_SECRET", "")
    if not configured:
        raise RuntimeError("SESSION_SIGNING_SECRET is not configured")
    return hashlib.sha256(configured.encode()).digest()


def fernet() -> Fernet:
    return Fernet(__import__("base64").urlsafe_b64encode(session_key()))


def seal(payload: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + SESSION_TTL}
    import json
    return fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def unseal(value: str) -> dict[str, Any]:
    try:
        import json
        raw = fernet().decrypt(value.encode(), ttl=SESSION_TTL)
        data = json.loads(raw.decode())
        if int(data.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return data
    except (InvalidToken, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired session") from exc


class ResultRequest(BaseModel):
    session: str = Field(min_length=20, max_length=4096)
    examination_name: str = Field(regex=r"^\d+$", max_length=10)
    year: str = Field(regex=r"^\d{4}$")
    examination_roll: str = Field(regex=r"^\d{5,11}$")
    registration_no: str = Field(regex=r"^\d{5,11}$")
    captcha: str = Field(regex=r"^\d{1,5}$")


EXAMINATIONS = {
    "2201": "Bachelor Degree Honours 1st Year",
    "2202": "Bachelor Degree Honours 2nd Year",
    "2203": "Bachelor Degree Honours 3rd Year",
    "2204": "Bachelor Degree Honours 4th Year",
    "2205": "Bachelor Degree Honours Consolidated Result",
}


def result_value(soup: BeautifulSoup, label: str) -> str | None:
    for box in soup.select("div.p-3.rounded-3.bg-light"):
        label_el = box.find("span", class_=lambda c: c and "text-muted" in c)
        if label_el and label_el.get_text(" ", strip=True).lower() == label.lower():
            full = box.get_text(" ", strip=True)
            return full[len(label):].strip()
    return None


def grade_point(grade: str) -> float | None:
    return {"A+": 4.00, "A": 3.75, "A-": 3.50, "B+": 3.25, "B": 3.00, "B-": 2.75, "C+": 2.50, "C": 2.25, "D": 2.00, "F": 0.00}.get(grade.upper().strip())


def parse_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if "ONLINE RESULT SHEET" not in html and "Course wise Result" not in html and "Course Wise Result" not in html:
        return {"found": False}
    courses: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if "course code" not in headers or "letter grade" not in headers:
            continue
        tbody = table.find("tbody")
        if not tbody:
            continue
        for row in tbody.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if len(cells) >= 4:
                courses.append({"course_code": cells[0], "course_title": cells[1], "credit": cells[2], "grade": cells[3], "grade_point": grade_point(cells[3])})
        break
    total_credit = total_points = 0.0
    graded_count = 0
    for course in courses:
        try:
            credit = float(course["credit"])
            point = course["grade_point"]
            if point is not None:
                total_credit += credit
                total_points += credit * point
                graded_count += 1
        except (ValueError, TypeError):
            pass
    return {"found": True, "student": {
        "name": result_value(soup, "Name of Student"), "father": result_value(soup, "Father's Name"),
        "mother": result_value(soup, "Mother's Name"), "college": result_value(soup, "College"),
        "session": result_value(soup, "Session"), "student_type": result_value(soup, "Student Type"),
        "subject": result_value(soup, "Subject")},
        "courses": courses,
        "summary": {"total_courses": len(courses), "total_credit": round(total_credit, 2), "gpa": round(total_points / total_credit, 2) if total_credit and graded_count else None}}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def rate_limited(request: Request) -> bool:
    now = time.time()
    ip = client_ip(request)
    hits = [t for t in _rate_cache.get(ip, []) if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        _rate_cache[ip] = hits
        return True
    hits.append(now)
    _rate_cache[ip] = hits
    if len(_rate_cache) > 1000:
        for key in list(_rate_cache)[:100]:
            if not _rate_cache[key] or now - _rate_cache[key][-1] > RATE_WINDOW:
                _rate_cache.pop(key, None)
    return False


@app.get("/api/health")
def health():
    return {"ok": True, "service": "nu-results", "version": "2.1.0"}


@app.get("/api/examinations")
def examinations():
    return {"examinations": EXAMINATIONS}


@app.get("/api/captcha")
def captcha(request: Request):
    if rate_limited(request):
        return {"error": "Too many requests. Please wait a minute and try again."}
    try:
        client = requests.Session()
        response = client.get(NU_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        captcha_el = soup.select_one("span.fw-bold.fs-5")
        if not token_el or not captcha_el:
            return {"error": "NU result form could not be read."}
        return {"captcha": captcha_el.get_text(" ", strip=True), "session": seal({"csrf": token_el.get("value", ""), "cookies": client.cookies.get_dict()}), "expires_in": SESSION_TTL}
    except RuntimeError:
        return {"error": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"error": "Could not connect to the NU result server."}


@app.post("/api/result")
def search_result(body: ResultRequest, request: Request):
    if rate_limited(request):
        return {"found": False, "message": "Too many searches. Please wait a minute and try again."}
    if body.examination_name not in EXAMINATIONS:
        return {"found": False, "message": "Unsupported examination type."}
    try:
        state = unseal(body.session)
        csrf = state.get("csrf")
        cookies = state.get("cookies") or {}
        if not csrf:
            raise ValueError("missing csrf")
        client = requests.Session()
        client.cookies.update(cookies)
        response = client.post(NU_URL, data={"_token": csrf, "examination_name": body.examination_name, "year": body.year, "examination_roll": body.examination_roll, "registration_no": body.registration_no, "captcha": body.captcha}, timeout=28, allow_redirects=True)
        response.raise_for_status()
        parsed = parse_result(response.text)
        if not parsed.get("found"):
            return {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
        return parsed
    except ValueError:
        return {"found": False, "message": "Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError:
        return {"found": False, "message": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"found": False, "message": "NU result server is taking too long to respond. Please try again without changing your CAPTCHA."}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots(request: Request):
    base = str(request.base_url).rstrip("/")
    return f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n"


@app.get("/sitemap.xml", response_class=PlainTextResponse)
def sitemap(request: Request):
    base = str(request.base_url).rstrip("/")
    pages = ["/", "/how-to-use.html", "/grading.html", "/about.html", "/privacy.html", "/disclaimer.html"]
    urls = "".join(f"<url><loc>{base}{path}</loc></url>" for path in pages)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return PlainTextResponse(xml, media_type="application/xml")


# Keep public, clean URLs while storing informational pages in a dedicated directory.
for _page in ("how-to-use", "grading", "about", "privacy", "disclaimer"):
    def _serve_page(page: str = _page):
        return FileResponse(os.path.join(PAGES_DIR, f"{page}.html"))
    app.add_api_route(f"/{_page}.html", _serve_page, methods=["GET"], include_in_schema=False)


app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
