from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request

from api.common.security import SESSION_TTL, rate_limited, seal, unseal

MASTERS_URL = "https://results.nu.ac.bd/masters"
MASTERS_CAPTCHA_REFRESH_URL = "https://results.nu.ac.bd/refresh-captcha"
NU_ORIGIN = "https://results.nu.ac.bd"

MASTERS_EXAMINATIONS = {
    "3302": "Masters Final Result (Available from 2007)",
    "4301": "Preliminary to Master's Result (Available from 2005)",
    "3303": "ICT Course Result (Available from 2020)",
}

EXAMINATION_METRICS = {
    "3302": {"metric": "CGPA", "has_courses": True},
    "4301": {"metric": "CGPA", "has_courses": True},
    "3303": {"metric": "GPA", "has_courses": False},
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
HTML_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}

app = FastAPI(title="NU Masters Results API", version="1.6.1")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _result_section(soup: BeautifulSoup):
    return soup.select_one("#result-section") or soup


def _value(soup: BeautifulSoup, *labels: str) -> str | None:
    """Extract a labelled value from the official result HTML."""
    wanted = {_norm(label) for label in labels}
    scope = _result_section(soup)

    for row in scope.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = _norm(cells[0].get_text(" ", strip=True).rstrip(":"))
            if label in wanted:
                return _clean(cells[1].get_text(" ", strip=True))

    for node in scope.find_all(string=True):
        raw = _clean(str(node))
        if not raw:
            continue
        normalized = _norm(raw.rstrip(":"))
        if normalized in wanted:
            parent = node.parent
            if not parent:
                continue
            box = parent.parent or parent
            text = _clean(box.get_text(" ", strip=True)) or ""
            label_text = raw.rstrip(":")
            match = re.match(r"^" + re.escape(label_text) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
            if match:
                return _clean(match.group(1))
            siblings = list(box.find_all(recursive=False))
            seen = False
            for child in siblings:
                if child is parent:
                    seen = True
                    continue
                if seen:
                    value = _clean(child.get_text(" ", strip=True))
                    if value:
                        return value
            continue

        for label in labels:
            match = re.match(r"^" + re.escape(label) + r"\s*:\s*(.+)$", raw, re.I)
            if match:
                return _clean(match.group(1))
    return None


def _registration(soup: BeautifulSoup) -> str | None:
    scope = _result_section(soup)
    wanted = _norm("Registration No.")
    for node in scope.find_all(string=True):
        if _norm(_clean(str(node)) or "") != wanted:
            continue
        parent = node.parent
        if not parent:
            continue
        box = parent.parent or parent
        digits = "".join(re.findall(r"\d", box.get_text(" ", strip=True)))
        if 5 <= len(digits) <= 11:
            return digits
    value = _value(scope, "Registration No.", "Registration Number", "Registration")
    if value:
        digits = "".join(re.findall(r"\d", value))
        return digits or value
    return None


def _number(soup: BeautifulSoup, label: str) -> float | None:
    value = _value(soup, label)
    if not value:
        return None
    match = re.search(r"(?<!\d)([0-4](?:\.\d{1,2})?)(?!\d)", value)
    return round(float(match.group(1)), 2) if match else None


def _courses(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    scope = _result_section(soup)
    for table in scope.find_all("table"):
        headers = [_clean(cell.get_text(" ", strip=True)) or "" for cell in table.find_all("th")]
        normalized = [_norm(header) for header in headers]
        course_index = next((i for i, value in enumerate(normalized) if value == "coursecode"), None)
        title_index = next((i for i, value in enumerate(normalized) if value in {"titleofcourse", "coursetitle", "coursename"}), None)
        result_index = next((i for i, value in enumerate(normalized) if value in {"lettergrade", "grade", "result", "marks", "gradeormarks"}), None)
        credit_index = next((i for i, value in enumerate(normalized) if value in {"credit", "credits"}), None)
        if course_index is None or title_index is None or result_index is None:
            continue
        rows: list[dict[str, Any]] = []
        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = [_clean(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
            required = [course_index, title_index, result_index]
            if credit_index is not None:
                required.append(credit_index)
            if not cells or len(cells) <= max(required):
                continue
            code, title, result = cells[course_index], cells[title_index], cells[result_index]
            if not code or not title or not result or not re.fullmatch(r"\d{4,8}", code):
                continue
            rows.append({"course_code": code, "course_title": title, "credit": cells[credit_index] if credit_index is not None else None, "grade": result, "result": result})
        if rows:
            return rows, headers[result_index]
    return [], None


def _result_title(soup: BeautifulSoup) -> str | None:
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p"]):
        value = _clean(element.get_text(" ", strip=True))
        if value and "examination" in value.lower() and len(value) < 180:
            return value
    return None


def _generated_on(soup: BeautifulSoup) -> str | None:
    text = _result_section(soup).get_text(" ", strip=True)
    match = re.search(r"Generated\s+on\s+(.+)$", text, re.I)
    return _clean(match.group(1)) if match else None


def _result_metric(soup: BeautifulSoup) -> tuple[str | None, float | None]:
    title = (_result_title(soup) or "").lower()
    if "ict course" in title:
        return "GPA", _number(soup, "GPA")
    cgpa = _number(soup, "CGPA")
    if cgpa is not None:
        return "CGPA", cgpa
    gpa = _number(soup, "GPA")
    if gpa is not None:
        return "GPA", gpa
    return None, None


def _is_result_page(soup: BeautifulSoup) -> bool:
    section = soup.select_one("#result-section")
    if not section:
        return False
    text = section.get_text(" ", strip=True).lower()
    if "online result sheet" not in text:
        return False
    title = _result_title(soup)
    metric, value = _result_metric(soup)
    courses, _ = _courses(soup)
    return bool(title and ((metric is not None and value is not None) or courses))


def _examination_from_title(title: str | None) -> str | None:
    value = (title or "").lower()
    if "ict course" in value:
        return "3303"
    if "preliminary" in value:
        return "4301"
    if "masters final" in value:
        return "3302"
    return None


def parse_masters_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_result_page(soup):
        return {"found": False}

    title = _result_title(soup)
    examination = _examination_from_title(title)
    metric, official_value = _result_metric(soup)
    courses, result_label = _courses(soup)
    student = {
        "examination_roll": _value(soup, "Examination Roll", "Exam. Roll", "Exam Roll", "Roll No.", "Roll Number"),
        "registration_no": _registration(soup),
        "name": _value(soup, "Name of Student", "Student Name", "Name"),
        "father": _value(soup, "Father's Name", "Father Name", "Father"),
        "mother": _value(soup, "Mother's Name", "Mother"),
        "college": _value(soup, "College", "Name of College", "College Name"),
        "session": _value(soup, "Session", "Academic Session"),
        "student_type": _value(soup, "Student Type", "StudentType"),
        "subject": _value(soup, "Subject", "Subject Name", "Course", "Course Name"),
    }

    grade_points = {"A+": 4.0, "A": 3.75, "A-": 3.5, "B+": 3.25, "B": 3.0, "B-": 2.75, "C+": 2.5, "C": 2.25, "D": 2.0, "F": 0.0}
    total_credit = total_points = 0.0
    for course in courses:
        try:
            credit = float(course["credit"]) if course.get("credit") else 0.0
            grade_point = grade_points.get(str(course.get("grade") or "").upper().strip())
            if credit > 0 and grade_point is not None:
                total_credit += credit
                total_points += credit * grade_point
        except (TypeError, ValueError):
            continue
    calculated_gpa = round(total_points / total_credit, 2) if total_credit else None
    official_gpa = official_value if metric == "GPA" else None
    official_cgpa = official_value if metric == "CGPA" else None

    return {
        "found": True,
        "examination_name": examination,
        "result_metric": metric,
        "result_title": title,
        "student": student,
        "gpa": official_gpa,
        "cgpa": official_cgpa,
        "courses": courses,
        "summary": {
            "total_courses": len(courses),
            "total_credit": round(total_credit, 2) if total_credit else None,
            "calculated_gpa": calculated_gpa if courses else None,
            "gpa": official_gpa,
            "cgpa": official_cgpa,
        },
        "course_result_label": result_label,
        "dates": {"result_upload_date": _value(soup, "Result Upload Date"), "generated_on": _generated_on(soup)},
    }


def _form_from_response(response: requests.Response) -> tuple[str, str, str] | None:
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", method=lambda value: value and value.upper() == "POST")
    if not form:
        return None
    token = form.find("input", {"name": "_token"})
    captcha = form.select_one("span.fw-bold.fs-5") or form.select_one("span.fw-bold") or form.find(string=re.compile(r"\d+\s*\+\s*\d+\s*="))
    action = form.get("action")
    if not token or not captcha or not action:
        return None
    csrf = _clean(token.get("value"))
    question = _clean(captcha.get_text(" ", strip=True) if hasattr(captcha, "get_text") else str(captcha))
    action_url = urljoin(response.url, str(action))
    parsed_action = urlparse(action_url)
    if not csrf or not question or parsed_action.scheme != "https" or parsed_action.netloc != urlparse(NU_ORIGIN).netloc:
        return None
    return csrf, action_url, question


def _get_form(client: requests.Session) -> tuple[str, str, str] | None:
    headers = {**HTML_HEADERS, "Referer": f"{NU_ORIGIN}/"}
    last_error: requests.RequestException | None = None
    for url in (MASTERS_URL, f"{MASTERS_URL}?_={int(time.time())}"):
        try:
            response = client.get(url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()
            parsed = _form_from_response(response)
            if parsed:
                return parsed
        except requests.RequestException as exc:
            last_error = exc
    if last_error:
        raise last_error
    return None


def _captcha(request: Request) -> dict[str, Any]:
    if rate_limited(request):
        return {"error": "Too many requests. Please wait a minute and try again."}
    try:
        client = requests.Session()
        parsed = _get_form(client)
        if not parsed:
            return {"error": "NU Masters result form could not be read. Please try again."}
        csrf, action, question = parsed
        return {"captcha": question, "session": seal({"csrf": csrf, "cookies": client.cookies.get_dict(), "action": action, "module": "masters"}), "expires_in": SESSION_TTL}
    except RuntimeError:
        return {"error": "Server security configuration is incomplete."}
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        if code == 403:
            return {"error": "The NU Masters result server denied the CAPTCHA request. Please refresh and try again."}
        if code == 429:
            return {"error": "The NU Masters result server is rate-limiting requests. Please wait and try again."}
        return {"error": f"NU Masters result server returned HTTP {code} while loading CAPTCHA."}
    except requests.RequestException:
        return {"error": "Could not connect to the NU Masters result server."}


@app.get("/api/masters")
def masters_get(request: Request, action: str = "examinations"):
    if action == "examinations":
        return {"examinations": MASTERS_EXAMINATIONS}
    if action == "captcha":
        return _captcha(request)
    return {"error": "Unsupported Masters API action."}


@app.post("/api/masters")
def masters_result(body: dict[str, Any], request: Request):
    if rate_limited(request):
        return {"found": False, "message": "Too many searches. Please wait a minute and try again."}
    exam = str(body.get("examination_name", ""))
    year = str(body.get("year", ""))
    roll = str(body.get("examination_roll", ""))
    registration = str(body.get("registration_no", ""))
    captcha = str(body.get("captcha", ""))
    if exam not in MASTERS_EXAMINATIONS:
        return {"found": False, "message": "Unsupported Masters examination type."}
    if not re.fullmatch(r"\d{4}", year):
        return {"found": False, "message": "Please enter a valid 4-digit examination year."}
    if roll and not re.fullmatch(r"\d{5,11}", roll):
        return {"found": False, "message": "Exam roll must contain 5 to 11 digits."}
    if not re.fullmatch(r"\d{5,11}", registration):
        return {"found": False, "message": "Registration number must contain 5 to 11 digits."}
    if not re.fullmatch(r"\d{1,5}", captcha):
        return {"found": False, "message": "Please enter the numeric CAPTCHA answer."}
    try:
        state = unseal(str(body.get("session", "")))
        if state.get("module") != "masters":
            raise ValueError("wrong module")
        csrf, action, cookies = state.get("csrf"), state.get("action"), state.get("cookies") or {}
        if not csrf or not action:
            raise ValueError("missing session")
        action_url = urlparse(str(action))
        if action_url.scheme != "https" or action_url.netloc != urlparse(NU_ORIGIN).netloc:
            raise ValueError("invalid action")
        client = requests.Session()
        client.cookies.update(cookies)
        headers = {**HTML_HEADERS, "Referer": MASTERS_URL, "Origin": NU_ORIGIN, "Content-Type": "application/x-www-form-urlencoded", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-User": "?1", "Sec-Fetch-Dest": "document"}
        response = client.post(str(action), data={"_token": csrf, "examination_name": exam, "year": year, "examination_roll": roll, "registration_no": registration, "captcha": captcha}, headers=headers, timeout=28, allow_redirects=True)
        if response.status_code == 403:
            return {"found": False, "message": "The NU Masters result server denied the search request. Please refresh the CAPTCHA and try again."}
        if response.status_code == 429:
            return {"found": False, "message": "The NU Masters result server is rate-limiting searches. Please wait and try again."}
        response.raise_for_status()
        parsed = parse_masters_result(response.text)
        if not parsed.get("found"):
            text = response.text.lower()
            if "captcha" in text and ("invalid" in text or "incorrect" in text or "wrong" in text):
                return {"found": False, "message": "Incorrect CAPTCHA. Please enter the current CAPTCHA answer and try again."}
            return {"found": False, "message": "Result was not found. Check your details and CAPTCHA."}
        returned_exam = parsed.get("examination_name")
        if returned_exam and returned_exam != exam:
            return {"found": False, "message": "The NU result response did not match the selected examination."}
        return parsed
    except ValueError:
        return {"found": False, "message": "Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError:
        return {"found": False, "message": "Server security configuration is incomplete."}
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        return {"found": False, "message": f"NU Masters result server returned HTTP {code}. Please try again."}
    except requests.RequestException:
        return {"found": False, "message": "NU Masters result server is taking too long to respond. Please try again with a fresh CAPTCHA."}


__all__ = ["MASTERS_CAPTCHA_REFRESH_URL", "MASTERS_EXAMINATIONS", "MASTERS_URL", "EXAMINATION_METRICS", "app", "parse_masters_result"]
