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
        if len(cells) >= 2 and _norm(cells[0].get_text(" ", strip=True).rstrip(":")) in wanted:
            return _clean(cells[1].get_text(" ", strip=True))

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
        values = []
        for child in children:
            child_text = _clean(child.get_text(" ", strip=True))
            if child is parent:
                seen = True
                continue
            if seen and child_text:
                values.append(child_text)
        if values:
            return _clean(" ".join(values))
        text = _clean(container.get_text(" ", strip=True)) or ""
        match = re.search(r"^" + re.escape(label_text.rstrip(":")) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
        if match:
            return _clean(match.group(1))
    return None


def _extract_result_title(soup: BeautifulSoup) -> str | None:
    candidates = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p"]):
        text = _clean(element.get_text(" ", strip=True))
        if text and "degree pass" in text.lower() and "examination" in text.lower():
            candidates.append(text)
    return candidates[-1] if candidates else None


def _course_rows(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    courses: list[dict[str, Any]] = []
    result_label: str | None = None
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)) or "" for th in table.find_all("th")]
        normalized = [_norm(h) for h in headers]
        code_index = next((i for i, x in enumerate(normalized) if x in {"coursecode", "code"}), None)
        title_index = next((i for i, x in enumerate(normalized) if x in {"titleofcourse", "coursetitle", "coursename", "title"}), None)
        result_index = next((i for i, x in enumerate(normalized) if x in {"lettergrade", "grade", "marks", "marksgrade", "gradeormarks", "result"}), None)
        if code_index is None or title_index is None or result_index is None:
            continue
        result_label = headers[result_index] or None
        body = table.find("tbody") or table
        for row in body.find_all("tr"):
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all("td")]
            if len(cells) <= max(code_index, title_index, result_index):
                continue
            code, title, result = cells[code_index], cells[title_index], cells[result_index]
            if not code or not title or not result:
                continue
            if re.fullmatch(r"[A-Za-z0-9 .\-/()]+", code) is None:
                continue
            courses.append({"course_code": code, "course_title": title, "result": result})
        if courses:
            break
    return courses, result_label


def _extract_gpa(text: str) -> float | None:
    patterns = (
        r"(?:overall\s+)?gpa\s*(?:\([^)]*\))?\s*[:\-]?\s*([0-4](?:\.\d{1,2})?)\b",
        r"gpa\s*(?:of|=)\s*([0-4](?:\.\d{1,2})?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 4:
                return round(value, 2)
    return None


def _extract_date(text: str, label: str) -> str | None:
    match = re.search(re.escape(label) + r"\s*:?\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}(?:\s+[0-9]{1,2}:?[0-9]{2}(?:\s*[AP]M)?)?)", text, re.I)
    return _clean(match.group(1)) if match else None


def _is_degree_result(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return "degree pass" in text and "course code" in text and ("result" in text or "promoted" in text or "not promoted" in text)


def parse_degree_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_degree_result(soup):
        return {"found": False}
    text = soup.get_text(" ", strip=True)
    courses, result_label = _course_rows(soup)
    student = {
        "examination_roll": _value(soup, "Examination Roll", "Exam Roll", "Roll No.", "Roll No", "Roll Number", "Roll"),
        "registration_no": _value(soup, "Registration No.", "Registration No", "Registration Number"),
        "name": _value(soup, "Name of Student", "Student's Name", "Student Name", "Name"),
        "father": _value(soup, "Father's Name", "Father Name", "Father"),
        "mother": _value(soup, "Mother's Name", "Mother Name", "Mother"),
        "college": _value(soup, "College", "College Name"),
        "session": _value(soup, "Session", "Academic Session"),
        "student_type": _value(soup, "Student Type", "StudentType"),
        "course": _value(soup, "Course", "Course Name"),
    }
    result_status = _value(soup, "Result Status", "Result", "Final Result", "Status")
    if not result_status:
        match = re.search(r"\b(Promoted|Not Promoted|Passed|Failed|Withheld|Absent|Improved|Pass|Fail)\b", text, re.I)
        result_status = _clean(match.group(1)) if match else None
    gpa = _extract_gpa(text)
    summary = {"total_courses": len(courses)}
    if gpa is not None:
        summary["gpa"] = gpa
    return {
        "found": True,
        "result_title": _extract_result_title(soup),
        "student": student,
        "result_status": result_status,
        "gpa": gpa,
        "courses": courses,
        "summary": summary,
        "course_result_label": result_label,
        "dates": {
            "result_upload_date": _extract_date(text, "Result Upload Date"),
            "generated_on": _extract_date(text, "Generated on") or _extract_date(text, "Generated On"),
        },
    }
