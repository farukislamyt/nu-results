from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from api.common.security import SESSION_TTL, rate_limited, seal, unseal

NU_URL = "https://results.nu.ac.bd/honours"
EXAMINATIONS = {
    "2201": "Bachelor Degree Honours 1st Year",
    "2202": "Bachelor Degree Honours 2nd Year",
    "2203": "Bachelor Degree Honours 3rd Year",
    "2204": "Bachelor Degree Honours 4th Year",
    "2205": "Bachelor Degree Honours Consolidated Result",
}
router = APIRouter()

class ResultRequest(BaseModel):
    session: str = Field(min_length=20, max_length=4096)
    examination_name: str = Field(pattern=r"^\d+$", max_length=10)
    year: str = Field(pattern=r"^\d{4}$")
    examination_roll: str = Field(pattern=r"^\d{5,11}$")
    registration_no: str = Field(pattern=r"^\d{5,11}$")
    captcha: str = Field(pattern=r"^\d{1,5}$")


def result_value(soup: BeautifulSoup, label: str) -> str | None:
    for box in soup.select("div.p-3.rounded-3.bg-light"):
        label_el = box.find("span", class_=lambda c: c and "text-muted" in c)
        if label_el and label_el.get_text(" ", strip=True).lower() == label.lower():
            full = box.get_text(" ", strip=True)
            return full[len(label):].strip()
    return None


def grade_point(grade: str) -> float | None:
    return {"A+": 4.00, "A": 3.75, "A-": 3.50, "B+": 3.25, "B": 3.00, "B-": 2.75, "C+": 2.50, "C": 2.25, "D": 2.00, "F": 0.00}.get(grade.upper().strip())


def _parse_consolidated_courses(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Parse the official 2205 layout: four year columns containing nested Course Code/LG tables."""
    courses: list[dict[str, Any]] = []
    yearly_gpa: dict[str, float] = {}
    outer = None
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th", recursive=False)]
        if {"first year", "second year", "third year", "fourth year"}.issubset(set(headers)):
            outer = table
            break
    if outer is None:
        return courses, yearly_gpa

    year_names = ["First Year", "Second Year", "Third Year", "Fourth Year"]
    row = outer.find("tbody", recursive=False)
    cells = row.find("tr").find_all("td", recursive=False) if row and row.find("tr", recursive=False) else []
    for index, cell in enumerate(cells[:4]):
        year_name = year_names[index]
        nested = None
        for table in cell.find_all("table"):
            headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
            if "course code" in headers and "lg" in headers:
                nested = table
                break
        if nested is None:
            continue
        for tr in nested.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            code = tds[0].get_text(" ", strip=True)
            grade = tds[1].get_text(" ", strip=True)
            if not re.fullmatch(r"\d+(?:\(\d+\))?", code) or not re.fullmatch(r"[A-F][+-]?", grade, re.I):
                continue
            match = re.search(r"\((\d+)\)$", code)
            credit = match.group(1) if match else None
            course_code = code[:match.start()] if match else code
            courses.append({"course_code": course_code, "course_title": year_name, "credit": credit, "grade": grade, "grade_point": grade_point(grade), "year": year_name})

    gpa_row = outer.find("thead", recursive=False)
    if gpa_row:
        gpa_tr = gpa_row.find("tr")
        if gpa_tr:
            for index, td in enumerate(gpa_tr.find_all("td", recursive=False)[:4]):
                match = re.search(r"GPA\s*:\s*([0-9]+(?:\.[0-9]+)?)", td.get_text(" ", strip=True), re.I)
                if match:
                    yearly_gpa[year_names[index]] = float(match.group(1))
    return courses, yearly_gpa


def parse_result(html: str, examination_name: str | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if "ONLINE RESULT SHEET" not in html and "Course wise Result" not in html and "Course Wise Result" not in html:
        return {"found": False}
    courses: list[dict[str, Any]] = []
    yearly_gpa: dict[str, float] = {}
    if examination_name == "2205":
        courses, yearly_gpa = _parse_consolidated_courses(soup)
    if not courses:
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
    result: dict[str, Any] = {"found": True, "student": {"name": result_value(soup, "Name of Student"), "father": result_value(soup, "Father's Name"), "mother": result_value(soup, "Mother's Name"), "college": result_value(soup, "College"), "session": result_value(soup, "Session"), "student_type": result_value(soup, "Student Type"), "subject": result_value(soup, "Subject")}, "courses": courses, "summary": {"total_courses": len(courses), "total_credit": round(total_credit, 2), "gpa": round(total_points / total_credit, 2) if total_credit and graded_count else None}}
    if yearly_gpa:
        result["summary"]["yearly_gpa"] = yearly_gpa
        cgpa_el = soup.find(string=re.compile(r"^\s*CGPA\s*$", re.I))
        if cgpa_el:
            container = cgpa_el.parent.parent if cgpa_el.parent else None
            value = container.get_text(" ", strip=True) if container else ""
            match = re.search(r"CGPA\s*([0-9]+(?:\.[0-9]+)?)", value, re.I)
            if match:
                result["summary"]["official_cgpa"] = float(match.group(1))
    return result


def fetch_captcha(request: Request) -> dict[str, Any]:
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
        return {"captcha": captcha_el.get_text(" ", strip=True), "session": seal({"csrf": token_el.get("value", ""), "cookies": client.cookies.get_dict(), "module": "honours"}), "expires_in": SESSION_TTL}
    except RuntimeError:
        return {"error": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"error": "Could not connect to the NU result server."}


@router.get("/api/examinations")
def examinations():
    return {"examinations": EXAMINATIONS}

@router.get("/api/captcha")
def captcha(request: Request):
    return fetch_captcha(request)

@router.post("/api/result")
def search_result(body: ResultRequest, request: Request):
    if rate_limited(request):
        return {"found": False, "message": "Too many searches. Please wait a minute and try again."}
    if body.examination_name not in EXAMINATIONS:
        return {"found": False, "message": "Unsupported examination type."}
    try:
        state = unseal(body.session)
        if state.get("module") != "honours":
            raise ValueError("wrong module")
        csrf = state.get("csrf")
        cookies = state.get("cookies") or {}
        if not csrf:
            raise ValueError("missing csrf")
        client = requests.Session()
        client.cookies.update(cookies)
        response = client.post(NU_URL, data={"_token": csrf, "examination_name": body.examination_name, "year": body.year, "examination_roll": body.examination_roll, "registration_no": body.registration_no, "captcha": body.captcha}, timeout=28, allow_redirects=True)
        response.raise_for_status()
        parsed = parse_result(response.text, body.examination_name)
        return parsed if parsed.get("found") else {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
    except ValueError:
        return {"found": False, "message": "Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError:
        return {"found": False, "message": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"found": False, "message": "NU result server is taking too long to respond. Please try again without changing your CAPTCHA."}

__all__ = ["EXAMINATIONS", "ResultRequest", "fetch_captcha", "grade_point", "parse_result", "router"]
