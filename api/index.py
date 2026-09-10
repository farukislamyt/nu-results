import base64
import hashlib
import hmac
import json
import os
from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="NU Results API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

NU_URL = "https://results.nu.ac.bd/honours"


def secret() -> bytes:
    return os.environ.get("SESSION_SIGNING_SECRET", "dev-only-change-me").encode()


def seal(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret(), raw, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{token}.{sig}"


def unseal(value: str) -> dict[str, Any]:
    try:
        encoded, sig = value.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        expected = hmac.new(secret(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("invalid signature")
        return json.loads(raw.decode())
    except Exception as exc:
        raise ValueError("Invalid or expired session") from exc


class ResultRequest(BaseModel):
    session: str
    examination_name: str = Field(pattern=r"^\d+$", max_length=10)
    year: str = Field(pattern=r"^\d{4}$")
    examination_roll: str = Field(pattern=r"^\d{5,11}$")
    registration_no: str = Field(pattern=r"^\d{5,11}$")
    captcha: str = Field(pattern=r"^\d{1,5}$")


def result_value(soup: BeautifulSoup, label: str) -> str | None:
    for box in soup.select("div.p-3.rounded-3.bg-light"):
        label_el = box.find("span", class_=lambda c: c and "text-muted" in c)
        if not label_el:
            continue
        if label_el.get_text(" ", strip=True).lower() == label.lower():
            full = box.get_text(" ", strip=True)
            return full[len(label):].strip()
    return None


def parse_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if "ONLINE RESULT SHEET" not in html and "Course wise Result" not in html:
        return {"found": False}

    courses: list[dict[str, str]] = []
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
                courses.append({
                    "course_code": cells[0],
                    "course_title": cells[1],
                    "credit": cells[2],
                    "grade": cells[3],
                })
        break

    return {
        "found": True,
        "student": {
            "name": result_value(soup, "Name of Student"),
            "father": result_value(soup, "Father's Name"),
            "mother": result_value(soup, "Mother's Name"),
            "college": result_value(soup, "College"),
            "session": result_value(soup, "Session"),
            "student_type": result_value(soup, "Student Type"),
            "subject": result_value(soup, "Subject"),
        },
        "courses": courses,
    }


@app.get("/api/health")
def health():
    return {"ok": True, "service": "nu-results"}


@app.get("/api/captcha")
def captcha():
    try:
        client = requests.Session()
        response = client.get(NU_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        captcha_el = soup.select_one("span.fw-bold.fs-5")
        if not token_el or not captcha_el:
            return {"error": "NU result form could not be read."}
        return {
            "captcha": captcha_el.get_text(" ", strip=True),
            "session": seal({"csrf": token_el.get("value", ""), "cookies": client.cookies.get_dict()}),
        }
    except requests.RequestException:
        return {"error": "Could not connect to the NU result server."}


@app.post("/api/result")
def search_result(body: ResultRequest):
    try:
        state = unseal(body.session)
        client = requests.Session()
        client.cookies.update(state.get("cookies", {}))
        data = {
            "_token": state["csrf"],
            "examination_name": body.examination_name,
            "year": body.year,
            "examination_roll": body.examination_roll,
            "registration_no": body.registration_no,
            "captcha": body.captcha,
        }
        response = client.post(NU_URL, data=data, timeout=20, allow_redirects=True)
        response.raise_for_status()
        parsed = parse_result(response.text)
        if not parsed.get("found"):
            return {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
        return parsed
    except ValueError:
        return {"found": False, "message": "Search session is invalid. Please refresh the CAPTCHA."}
    except requests.RequestException:
        return {"found": False, "message": "NU result server is temporarily unavailable."}
