from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.common.security import SESSION_TTL, rate_limited, seal, unseal
from api.degree import DEGREE_EXAMINATIONS, DEGREE_URL, parse_degree_result
from api.honours import EXAMINATIONS, grade_point, parse_result, router as honours_router

app = FastAPI(title="NU Results API", version="2.3.0")
app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Accept"])
app.include_router(honours_router)

class DegreeResultRequest(BaseModel):
    session: str = Field(min_length=20, max_length=4096)
    examination_name: str = Field(pattern=r"^\d+$", max_length=10)
    year: str = Field(pattern=r"^\d{4}$")
    examination_roll: str = Field(default="", pattern=r"^$|^\d{5,11}$")
    registration_no: str = Field(pattern=r"^\d{5,11}$")
    captcha: str = Field(pattern=r"^\d{1,5}$")


def fetch_degree_captcha(request: Request) -> dict[str, Any]:
    if rate_limited(request):
        return {"error": "Too many requests. Please wait a minute and try again."}
    try:
        client = requests.Session()
        response = client.get(DEGREE_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        captcha_el = soup.select_one("span.fw-bold.fs-5")
        if not token_el or not captcha_el:
            return {"error": "NU result form could not be read."}
        return {"captcha": captcha_el.get_text(" ", strip=True), "session": seal({"csrf": token_el.get("value", ""), "cookies": client.cookies.get_dict(), "module": "degree"}), "expires_in": SESSION_TTL}
    except RuntimeError:
        return {"error": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"error": "Could not connect to the NU result server."}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "nu-results", "version": "2.3.0"}


@app.get("/api/degree/examinations")
def degree_examinations():
    return {"examinations": DEGREE_EXAMINATIONS}


@app.get("/api/degree/captcha")
def degree_captcha(request: Request):
    return fetch_degree_captcha(request)


@app.post("/api/degree/result")
def search_degree_result(body: DegreeResultRequest, request: Request):
    if rate_limited(request):
        return {"found": False, "message": "Too many searches. Please wait a minute and try again."}
    if body.examination_name not in DEGREE_EXAMINATIONS:
        return {"found": False, "message": "Unsupported Degree examination type."}
    try:
        state = unseal(body.session)
        if state.get("module") != "degree":
            raise ValueError("wrong module")
        csrf = state.get("csrf")
        cookies = state.get("cookies") or {}
        if not csrf:
            raise ValueError("missing csrf")
        client = requests.Session()
        client.cookies.update(cookies)
        response = client.post(DEGREE_URL, data={"_token": csrf, "examination_name": body.examination_name, "year": body.year, "examination_roll": body.examination_roll, "registration_no": body.registration_no, "captcha": body.captcha}, timeout=28, allow_redirects=True)
        response.raise_for_status()
        parsed = parse_degree_result(response.text)
        return parsed if parsed.get("found") else {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
    except ValueError:
        return {"found": False, "message": "Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError:
        return {"found": False, "message": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"found": False, "message": "NU result server is taking too long to respond. Please try again without changing your CAPTCHA."}

__all__ = ["EXAMINATIONS", "app", "grade_point", "parse_result", "seal", "unseal"]
