from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

MASTERS_URL = "https://results.nu.ac.bd/masters"

# These are the examination codes used by the NU Masters result archive.
MASTERS_EXAMINATIONS = {
    "3301": "Preliminary to Masters",
    "3302": "Masters Final",
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

    for element in soup.find_all(string=True):
        label_text = _clean(str(element))
        if not label_text or _norm(label_text.rstrip(":")) not in wanted:
            continue
        parent = element.parent
        if not parent:
            continue
        container = parent.parent or parent
        children = [c for c in container.find_all(recursive=False)]
        if len(children) >= 2:
            seen = False
            values: list[str] = []
            for child in children:
                text = _clean(child.get_text(" ", strip=True))
                if not text:
                    continue
                if child is parent:
                    seen = True
                    continue
                if seen:
                    values.append(text)
            if values:
                return _clean(" ".join(values))
        text = _clean(container.get_text(" ", strip=True))
        if text:
            match = re.search(r"^" + re.escape(label_text.rstrip(":")) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
            if match:
                return _clean(match.group(1))
    return None


def _extract_number(text: str, *labels: str) -> float | None:
    for label in labels:
        match = re.search(r"(?:" + re.escape(label) + r")\s*(?:[:=\-])?\s*([0-4](?:\.\d{1,2})?)\b", text, re.I)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 4:
                return round(value, 2)
    return None


def _course_rows(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    courses: list[dict[str, Any]] = []
    result_label: str | None = None

    for table in soup.find_all("table"):
        headers = [_clean(th.get_text(" ", strip=True)) or "" for th in table.find_all("th")]
        normalized = [_norm(h) for h in headers]
        if not normalized:
            continue
        code_index = next((i for i, x in enumerate(normalized) if x in {"coursecode", "code", "course"}), None)
        title_index = next((i for i, x in enumerate(normalized) if x in {"coursetitle", "titleofcourse", "coursename", "title"}), None)
        credit_index = next((i for i, x in enumerate(normalized) if x in {"credit", "credits"}), None)
        result_index = next((i for i, x in enumerate(normalized) if x in {"lettergrade", "ltrgrade", "grade", "marks", "marksgrade", "gradeormarks", "obtainedgrade", "result"}), None)
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
            if re.fullmatch(r"[A-Za-z0-9 .\-/()]+", code) is None:
                continue
            credit = cells[credit_index] if credit_index is not None else None
            courses.append({"course_code": code, "course_title": title, "credit": credit, "grade": result, "result": result})
        if courses:
            break

    return courses, result_label


def _is_masters_result(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return "masters" in text and ("result sheet" in text or "course wise" in text or "course-wise" in text)


def parse_masters_result(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if not _is_masters_result(soup):
        return {"found": False}

    text = soup.get_text(" ", strip=True)
    courses, result_label = _course_rows(soup)
    cgpa = _extract_number(text, "CGPA", "Cumulative GPA")
    gpa = _extract_number(text, "GPA")

    student = {
        "examination_roll": _value(soup, "Examination Roll", "Exam. Roll", "Exam Roll", "Roll No.", "Roll No", "Roll Number", "Roll"),
        "registration_no": _value(soup, "Registration", "Registration No.", "Registration No", "Registration Number"),
        "name": _value(soup, "Name of Student", "Student's Name", "Student Name", "Name"),
        "father": _value(soup, "Father's Name", "Father Name", "Father"),
        "mother": _value(soup, "Mother's Name", "Mother Name", "Mother"),
        "college": _value(soup, "Name of College", "College", "College Name"),
        "session": _value(soup, "Session", "Academic Session"),
        "student_type": _value(soup, "Student Type", "StudentType"),
        "subject": _value(soup, "Subject Name", "Subject", "Course", "Course Name"),
    }

    title = None
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "div"]):
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

    total_credit = 0.0
    total_points = 0.0
    graded = 0
    grade_points = {"A+": 4.0, "A": 3.75, "A-": 3.5, "B+": 3.25, "B": 3.0, "B-": 2.75, "C+": 2.5, "C": 2.25, "D": 2.0, "F": 0.0}
    for course in courses:
        try:
            credit = float(course.get("credit")) if course.get("credit") else None
            point = grade_points.get(str(course.get("grade") or "").upper().strip())
            if credit is not None and point is not None:
                total_credit += credit
                total_points += credit * point
                graded += 1
        except (TypeError, ValueError):
            pass
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
    }
