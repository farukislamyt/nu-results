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


def _value(soup: BeautifulSoup, labels: str | tuple[str, ...]) -> str | None:
    if isinstance(labels, str):
        labels = (labels,)
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
                text = _clean(parent.parent.get_text(" ", strip=True) if parent.parent else parent.get_text(" ", strip=True))
                if text:
                    match = re.search(re.escape(label) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
                    if match:
                        return _clean(match.group(1))
    return None


def _course_rows(soup: BeautifulSoup) -> list[dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)).lower() if th.get_text(strip=True) else "" for th in table.find_all("th")]
        normalized = [_norm(h) for h in headers]
        if "coursecode" not in normalized or "coursetitle" not in normalized or not any(x in normalized for x in ("ltrgrade", "marksgrade", "grade", "marks")):
            continue
        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all("td")]
            if len(cells) < 3:
                continue
            code, title, result = cells[0], cells[1], cells[-1]
            if not code or not title or not result:
                continue
            if re.fullmatch(r"[A-Za-z0-9 .\-/]+", code) is None:
                continue
            courses.append({"course_code": code, "course_title": title, "result": result})
        if courses:
            break
    return courses


def _is_degree_result(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return (
        "online result sheet" in text or "result sheet" in text
    ) and "coursewise grade / marks" in text and "course code" in text


def parse_degree_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_degree_result(soup):
        return {"found": False}

    courses = _course_rows(soup)
    student = {
        "examination_roll": _value(soup, ("Examination Roll", "Roll No.", "Roll No")),
        "registration_no": _value(soup, ("Registration No.", "Registration No")),
        "name": _value(soup, ("Name of Student", "Student's Name", "Students Name")),
        "father": _value(soup, ("Father's Name", "Father Name")),
        "mother": _value(soup, ("Mother's Name", "Mother Name")),
        "college": _value(soup, "College"),
        "session": _value(soup, "Session"),
        "student_type": _value(soup, "Student Type"),
        "course": _value(soup, "Course"),
    }

    result_status = _value(soup, ("Result", "Result Status"))
    if not result_status:
        match = re.search(r"\b(Promoted|Not Promoted|Passed|Failed|Improved|Withheld|Absent)\b", soup.get_text(" ", strip=True), re.I)
        result_status = _clean(match.group(1)) if match else None

    gpa = None
    gpa_match = re.search(r"\bGPA(?:\s*\([^)]*\))?\s*:?\s*([0-4](?:\.\d{1,2})?)\b", soup.get_text(" ", strip=True), re.I)
    if gpa_match:
        gpa = float(gpa_match.group(1))

    text = soup.get_text(" ", strip=True)
    upload_match = re.search(r"Result Upload Date\s*:?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", text, re.I)
    generated_match = re.search(r"Generated on\s*:?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", text, re.I)

    return {
        "found": True,
        "student": student,
        "result_status": result_status,
        "courses": courses,
        "summary": {"total_courses": len(courses), "gpa": gpa},
        "dates": {
            "result_upload_date": upload_match.group(1) if upload_match else None,
            "generated_on": generated_match.group(1) if generated_match else None,
        },
    }
