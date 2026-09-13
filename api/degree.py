from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

DEGREE_URL = "https://results.nu.ac.bd/degree"
DEGREE_CAPTCHA_REFRESH_URL = "https://results.nu.ac.bd/degree/refresh-captcha"

DEGREE_EXAMINATIONS = {
    "1101": "Bachelor Degree Pass 1st Year",
    "1102": "Bachelor Degree Pass 2nd Year",
    "1103": "Bachelor Degree Pass 3rd Year",
    "1104": "Degree Pass Consolidated Result",
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
        if len(cells) >= 2:
            key = _norm(cells[0].get_text(" ", strip=True))
            if key in wanted:
                return _clean(cells[1].get_text(" ", strip=True))
    for label in labels:
        for element in soup.find_all(string=re.compile(re.escape(label), re.I)):
            parent = element.parent
            if parent:
                container = parent.parent or parent
                text = _clean(container.get_text(" ", strip=True))
                if text:
                    match = re.search(re.escape(label) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
                    if match:
                        return _clean(match.group(1))
    return None


def _course_rows(soup: BeautifulSoup) -> list[dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)) or "" for th in table.find_all("th")]
        normalized = [_norm(h) for h in headers]
        has_code = any(x in normalized for x in ("coursecode", "code"))
        has_title = any(x in normalized for x in ("titleofcourse", "coursetitle", "coursename", "title"))
        has_result = any(x in normalized for x in ("lettergrade", "grade", "marks", "marksgrade", "gradeorpoint", "result"))
        if not (has_code and has_title and has_result):
            continue

        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all("td")]
            if len(cells) < 3:
                continue
            code, title = cells[0], cells[1]
            result = cells[-1]
            if not code or not title or not result:
                continue
            if re.fullmatch(r"[A-Za-z0-9 .\-/()]+", code) is None:
                continue
            courses.append({"course_code": code, "course_title": title, "result": result})
        if courses:
            break
    return courses


def _extract_gpa(text: str) -> str | None:
    patterns = (
        r"(?:overall\s+)?gpa\s*(?:\([^)]*\))?\s*[:\-]?\s*([0-4](?:\.\d{1,2})?)",
        r"gpa\s*(?:of|=)\s*([0-4](?:\.\d{1,2})?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 4:
                return f"{value:.2f}"
    return None


def _extract_date(text: str, label: str) -> str | None:
    match = re.search(
        re.escape(label) + r"\s*:?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}(?:\s+[0-9]{1,2}:?[0-9]{2}(?:\s*[AP]M)?)?)",
        text,
        re.I,
    )
    return _clean(match.group(1)) if match else None


def _is_degree_result(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return (
        "online result sheet" in text
        and "course code" in text
        and ("result" in text or "promoted" in text)
    )


def parse_degree_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_degree_result(soup):
        return {"found": False}

    text = soup.get_text(" ", strip=True)
    courses = _course_rows(soup)

    student = {
        "examination_roll": _value(soup, "Examination Roll", "Roll No.", "Roll No", "Roll"),
        "registration_no": _value(soup, "Registration No.", "Registration No", "Registration Number"),
        "name": _value(soup, "Name of Student", "Student Name", "Name"),
        "father": _value(soup, "Father's Name", "Father Name", "Father"),
        "mother": _value(soup, "Mother's Name", "Mother Name", "Mother"),
        "college": _value(soup, "College", "College Name"),
        "session": _value(soup, "Session", "Academic Session"),
        "student_type": _value(soup, "Student Type", "StudentType"),
        "course": _value(soup, "Course", "Course Name"),
    }

    result_status = _value(soup, "Result Status", "Result", "Final Result", "Status")
    if not result_status:
        match = re.search(r"\b(Promoted|Not Promoted|Passed|Failed|Withheld|Absent|Pass|Fail)\b", text, re.I)
        result_status = _clean(match.group(1)) if match else None

    gpa = _extract_gpa(text)
    result_upload_date = _extract_date(text, "Result Upload Date")
    generated_on = _extract_date(text, "Generated on") or _extract_date(text, "Generated On")

    return {
        "found": True,
        "student": student,
        "result_status": result_status,
        "gpa": float(gpa) if gpa is not None else None,
        "courses": courses,
        "summary": {"total_courses": len(courses), "gpa": float(gpa) if gpa is not None else None},
        "dates": {
            "result_upload_date": result_upload_date,
            "generated_on": generated_on,
        },
    }
