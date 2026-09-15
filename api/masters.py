from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request

from api.index import rate_limited, seal, unseal

MASTERS_URL = "https://results.nu.ac.bd/masters"
MASTERS_CAPTCHA_REFRESH_URL = "https://results.nu.ac.bd/refresh-captcha"

# Confirmed from the real NU Masters search HTML.
MASTERS_EXAMINATIONS = {
    "3302": "Masters Final Result (Available from 2007)",
    "4301": "Preliminary to Master's Result (Available from 2005)",
    "3303": "ICT Course Result (Available from 2020)",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _value(soup: BeautifulSoup, *labels: str) -> str | None:
    wanted = {_norm(label) for label in labels}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2 and _norm(cells[0].get_text(" ", strip=True).rstrip(":")) in wanted:
            return _clean(cells[1].get_text(" ", strip=True))

    # Supports the real Masters result card, where label/value are sibling
    # elements rather than table cells.
    for element in soup.find_all(string=True):
        label_text = _clean(str(element))
        if not label_text or _norm(label_text.rstrip(":")) not in wanted:
            continue
        parent = element.parent
        if not parent:
            continue
        container = parent.parent or parent
        children = list(container.find_all(recursive=False))
        seen = False
        for child in children:
            text = _clean(child.get_text(" ", strip=True))
            if child is parent:
                seen = True
                continue
            if seen and text:
                return text
        text = _clean(container.get_text(" ", strip=True))
        if text:
            match = re.search(
                r"^" + re.escape(label_text.rstrip(":")) + r"\s*:?[\-]?\s*(.+)$",
                text,
                re.I,
            )
            if match:
                return _clean(match.group(1))
    return None


def _labeled_number(soup: BeautifulSoup, label: str) -> float | None:
    wanted = _norm(label)
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2 and _norm(cells[0].get_text(" ", strip=True).rstrip(":")) == wanted:
            match = re.search(r"\b([0-4](?:\.\d{1,2})?)\b", cells[1].get_text(" ", strip=True))
            return round(float(match.group(1)), 2) if match else None

    # Prefer an element whose visible label is exactly the requested label.
    for element in soup.find_all(string=True):
        if _norm(_clean(str(element)) or "") != wanted:
            continue
        parent = element.parent
        if not parent:
            continue
        text = _clean((parent.parent or parent).get_text(" ", strip=True)) or ""
        match = re.search(r"\b" + re.escape(label) + r"\b\s*[:=]?\s*([0-4](?:\.\d{1,2})?)\b", text, re.I)
        if match:
            return round(float(match.group(1)), 2)
    return None


def _course_rows(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    courses: list[dict[str, Any]] = []
    result_label: str | None = None

    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)) or "" for th in table.find_all("th")]
        normalized = [_norm(h) for h in headers]
        if not normalized:
            continue

        code_index = next((i for i, x in enumerate(normalized) if x == "coursecode"), None)
        title_index = next((i for i, x in enumerate(normalized) if x in {"titleofcourse", "coursetitle", "coursename"}), None)
        credit_index = next((i for i, x in enumerate(normalized) if x in {"credit", "credits"}), None)
        result_index = next((i for i, x in enumerate(normalized) if x in {"lettergrade", "grade", "marks", "gradeormarks", "result"}), None)
        if code_index is None or title_index is None or result_index is None:
            continue

        result_label = headers[result_index] or None
        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all("td")]
            needed = max(code_index, title_index, result_index, credit_index or 0)
            if len(cells) <= needed:
                continue
            code, title, result = cells[code_index], cells[title_index], cells[result_index]
            if not code or not title or not result:
                continue
            # NU course codes are numeric in the supplied real result HTML.
            if not re.fullmatch(r"\d{4,8}", code):
                continue
            credit = cells[credit_index] if credit_index is not None else None
            courses.append({
                "course_code": code,
                "course_title": title,
                "credit": credit,
                "grade": result,
                "result": result,
            })
        if courses:
            break
    return courses, result_label


def _is_masters_result(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return "national university, bangladesh" in text and "masters" in text and "result sheet" in text


def parse_masters_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_masters_result(soup):
        return {"found": False}

    text = soup.get_text(" ", strip=True)
    courses, result_label = _course_rows(soup)

    # The real Masters Final page labels this value exactly as CGPA. Do not
    # search for generic "GPA" because "GPA" is a substring of "CGPA".
    cgpa = _labeled_number(soup, "CGPA")
    gpa = _labeled_number(soup, "GPA")

    student = {
        "examination_roll": _value(soup, "Examination Roll", "Exam. Roll", "Exam Roll", "Roll No.", "Roll No", "Roll Number", "Roll"),
        "registration_no": _value(soup, "Registration No.", "Registration No", "Registration", "Registration Number"),
        "name": _value(soup, "Name of Student", "Student's Name", "Student Name", "Name"),
        "father": _value(soup, "Father's Name", "Father Name", "Father"),
        "mother": _value(soup, "Mother's Name", "Mother Name", "Mother"),
        "college": _value(soup, "College", "Name of College", "College Name"),
        "session": _value(soup, "Session", "Academic Session"),
        "student_type": _value(soup, "Student Type", "StudentType"),
        "subject": _value(soup, "Subject", "Subject Name", "Course", "Course Name"),
    }

    title = None
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p"]):
        candidate = _clean(element.get_text(" ", strip=True))
        if candidate and "masters" in candidate.lower() and "examination" in candidate.lower() and len(candidate) < 180:
            title = candidate
    if not title:
        match = re.search(r"(Masters[^|]{0,100}Examination[^|]{0,40})", text, re.I)
        title = _clean(match.group(1)) if match else None

    status = _value(soup, "Result Status", "Result", "Final Result", "Status")
    if not status:
        match = re.search(r"\b(Promoted|Not Promoted|Passed|Failed|Withheld|Absent|Improved|Pass|Fail)\b", text, re.I)
        status = _clean(match.group(1)) if match else None

    upload_date = _value(soup, "Result Upload Date")
    generated_on = _value(soup, "Generated on", "Generated On")

    grade_points = {
        "A+": 4.0, "A": 3.75, "A-": 3.5,
        "B+": 3.25, "B": 3.0, "B-": 2.75,
        "C+": 2.5, "C": 2.25, "D": 2.0, "F": 0.0,
    }
    total_credit = 0.0
    total_points = 0.0
    graded = 0
    for course in courses:
        try:
            credit = float(course["credit"]) if course.get("credit") else None
            point = grade_points.get(str(course.get("grade") or "").upper().strip())
            if credit is not None and point is not None:
                total_credit += credit
                total_points += credit * point
                graded += 1
        except (TypeError, ValueError):
            continue

    calculated_gpa = round(total_points / total_credit, 2) if total_credit and graded else None

    return {
        "found": True,
        "result_title": title,
        "student": student,
        "gpa": gpa,
        "cgpa": cgpa,
        "result_status": status,
        "courses": courses,
        "summary": {
            "total_courses": len(courses),
            "total_credit": round(total_credit, 2) if total_credit else None,
            "calculated_gpa": calculated_gpa,
            "gpa": gpa,
            "cgpa": cgpa,
        },
        "course_result_label": result_label,
        "dates": {"result_upload_date": upload_date, "generated_on": generated_on},
    }


app = FastAPI(title="NU Masters Results API", version="1.1.0")


def _captcha_response(request: Request) -> dict[str, Any]:
    if rate_limited(request):
        return {"error": "Too many requests. Please wait a minute and try again."}
    try:
        client = requests.Session()
        response = client.get(MASTERS_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", method=lambda value: value and value.upper() == "POST")
        token_el = soup.find("input", {"name": "_token"})
        captcha_el = soup.select_one("span.fw-bold.fs-5")
        if not form or not token_el or not captcha_el:
            return {"error": "NU Masters result form could not be read."}

        action = urljoin(MASTERS_URL, form.get("action") or MASTERS_URL)
        return {
            "captcha": captcha_el.get_text(" ", strip=True),
            "session": seal({
                "csrf": token_el.get("value", ""),
                "cookies": client.cookies.get_dict(),
                "action": action,
                "module": "masters",
            }),
            "expires_in": 300,
        }
    except RuntimeError:
        return {"error": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"error": "Could not connect to the NU Masters result server."}


@app.get("/api/masters")
def masters_get(action: str = "examinations", request: Request = None):
    if action == "examinations":
        return {"examinations": MASTERS_EXAMINATIONS}
    if action == "captcha":
        return _captcha_response(request)
    return {"error": "Unsupported Masters API action."}


@app.post("/api/masters")
def masters_result(body: dict[str, Any], request: Request):
    if rate_limited(request):
        return {"found": False, "message": "Too many searches. Please wait a minute and try again."}

    examination_name = str(body.get("examination_name", ""))
    if examination_name not in MASTERS_EXAMINATIONS:
        return {"found": False, "message": "Unsupported Masters examination type."}

    try:
        state = unseal(str(body.get("session", "")))
        if state.get("module") != "masters":
            raise ValueError("wrong module")
        csrf = state.get("csrf")
        cookies = state.get("cookies") or {}
        action = state.get("action")
        if not csrf or not action:
            raise ValueError("missing search session")

        client = requests.Session()
        client.cookies.update(cookies)
        response = client.post(
            str(action),
            data={
                "_token": csrf,
                "examination_name": examination_name,
                "year": str(body.get("year", "")),
                "examination_roll": str(body.get("examination_roll", "")),
                "registration_no": str(body.get("registration_no", "")),
                "captcha": str(body.get("captcha", "")),
            },
            timeout=28,
            allow_redirects=True,
        )
        response.raise_for_status()
        parsed = parse_masters_result(response.text)
        if not parsed.get("found"):
            return {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
        return parsed
    except ValueError:
        return {"found": False, "message": "Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError:
        return {"found": False, "message": "Server security configuration is incomplete."}
    except requests.RequestException:
        return {"found": False, "message": "NU Masters result server is taking too long to respond. Please try again without changing your CAPTCHA."}


__all__ = ["MASTERS_CAPTCHA_REFRESH_URL", "MASTERS_EXAMINATIONS", "MASTERS_URL", "parse_masters_result"]
