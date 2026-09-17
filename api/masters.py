from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request

from api.common.security import rate_limited, seal, unseal

MASTERS_URL = "https://results.nu.ac.bd/masters"
MASTERS_CAPTCHA_REFRESH_URL = "https://results.nu.ac.bd/refresh-captcha"
MASTERS_EXAMINATIONS = {
    "3302": "Masters Final Result (Available from 2007)",
    "4301": "Preliminary to Master's Result (Available from 2005)",
    "3303": "ICT Course Result (Available from 2020)",
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
HTML_HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9", "Cache-Control": "no-cache"}
GRADE_POINTS = {"A+": 4.0, "A": 3.75, "A-": 3.5, "B+": 3.25, "B": 3.0, "B-": 2.75, "C+": 2.5, "C": 2.25, "D": 2.0, "F": 0.0}
app = FastAPI(title="NU Masters Results API", version="1.3.0")

def _clean(v: str | None) -> str | None:
    if v is None: return None
    v = re.sub(r"\s+", " ", v).strip()
    return v or None

def _norm(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", v.lower())

def _value(soup: BeautifulSoup, *labels: str) -> str | None:
    wanted = {_norm(x) for x in labels}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2 and _norm(cells[0].get_text(" ", strip=True).rstrip(":")) in wanted:
            return _clean(cells[1].get_text(" ", strip=True))
    for node in soup.find_all(string=True):
        label = _clean(str(node))
        if not label or _norm(label.rstrip(":")) not in wanted: continue
        parent = node.parent
        if not parent: continue
        box = parent.parent or parent
        text = _clean(box.get_text(" ", strip=True)) or ""
        m = re.search(r"^" + re.escape(label.rstrip(":")) + r"\s*:?[\-]?\s*(.+)$", text, re.I)
        if m: return _clean(m.group(1))
        children = list(box.find_all(recursive=False))
        seen = False
        for child in children:
            if child is parent: seen = True
            elif seen and _clean(child.get_text(" ", strip=True)): return _clean(child.get_text(" ", strip=True))
    return None

def _number(soup: BeautifulSoup, label: str) -> float | None:
    value = _value(soup, label)
    if not value: return None
    m = re.search(r"\b([0-4](?:\.\d{1,2})?)\b", value)
    return round(float(m.group(1)), 2) if m else None

def _courses(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    for table in soup.find_all("table"):
        headers = [_clean(x.get_text(" ", strip=True)) or "" for x in table.find_all("th")]
        n = [_norm(x) for x in headers]
        ci = next((i for i,x in enumerate(n) if x == "coursecode"), None)
        ti = next((i for i,x in enumerate(n) if x in {"titleofcourse", "coursetitle", "coursename"}), None)
        ri = next((i for i,x in enumerate(n) if x in {"lettergrade", "grade", "result", "marks", "gradeormarks"}), None)
        kri = next((i for i,x in enumerate(n) if x in {"credit", "credits"}), None)
        if ci is None or ti is None or ri is None: continue
        rows=[]; body=table.find("tbody") or table
        for row in body.find_all("tr"):
            cells=[_clean(x.get_text(" ", strip=True)) for x in row.find_all("td")]
            if len(cells)<=max(ci,ti,ri,kri or 0): continue
            code,title,result=cells[ci],cells[ti],cells[ri]
            if not code or not title or not result or not re.fullmatch(r"\d{4,8}",code): continue
            rows.append({"course_code":code,"course_title":title,"credit":cells[kri] if kri is not None else None,"grade":result,"result":result})
        if rows: return rows, headers[ri]
    return [], None

def parse_masters_result(html: str) -> dict[str, Any]:
    soup=BeautifulSoup(html,"html.parser"); text=soup.get_text(" ",strip=True)
    if "national university, bangladesh" not in text.lower() or "masters" not in text.lower() or "result sheet" not in text.lower(): return {"found":False}
    courses,result_label=_courses(soup); cgpa=_number(soup,"CGPA"); gpa=_number(soup,"GPA")
    student={"examination_roll":_value(soup,"Examination Roll","Exam. Roll","Exam Roll","Roll No.","Roll Number"),"registration_no":_value(soup,"Registration No.","Registration Number","Registration"),"name":_value(soup,"Name of Student","Student Name","Name"),"father":_value(soup,"Father's Name","Father Name","Father"),"mother":_value(soup,"Mother's Name","Mother Name","Mother"),"college":_value(soup,"College","Name of College","College Name"),"session":_value(soup,"Session","Academic Session"),"student_type":_value(soup,"Student Type","StudentType"),"subject":_value(soup,"Subject","Subject Name","Course","Course Name")}
    title=None
    for el in soup.find_all(["h1","h2","h3","h4","h5","p"]):
        t=_clean(el.get_text(" ",strip=True))
        if t and "masters" in t.lower() and "examination" in t.lower() and len(t)<180: title=t
    upload=_value(soup,"Result Upload Date"); generated=_value(soup,"Generated on","Generated On")
    total_credit=total_points=0.0
    for c in courses:
        try:
            cr=float(c["credit"]) if c.get("credit") else 0; gp=GRADE_POINTS.get(str(c.get("grade") or "").upper().strip())
            if cr and gp is not None: total_credit+=cr; total_points+=cr*gp
        except (TypeError,ValueError): pass
    calc=round(total_points/total_credit,2) if total_credit else None
    return {"found":True,"result_title":title,"student":student,"gpa":gpa,"cgpa":cgpa,"courses":courses,"summary":{"total_courses":len(courses),"total_credit":round(total_credit,2) if total_credit else None,"calculated_gpa":calc,"gpa":gpa,"cgpa":cgpa},"course_result_label":result_label,"dates":{"result_upload_date":upload,"generated_on":generated}}

def _get_form(client: requests.Session) -> tuple[str,str,str] | None:
    r=client.get(MASTERS_URL,headers=HTML_HEADERS,timeout=15); r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
    form=soup.find("form",method=lambda v:v and v.upper()=="POST")
    if not form: return None
    token=form.find("input",{"name":"_token"}); captcha=form.select_one("span.fw-bold.fs-5") or form.select_one("span.fw-bold")
    if not token or not captcha: return None
    csrf=_clean(token.get("value")); question=_clean(captcha.get_text(" ",strip=True))
    if not csrf or not question: return None
    return csrf,urljoin(MASTERS_URL,form.get("action") or MASTERS_URL),question

def _captcha(request: Request) -> dict[str,Any]:
    if rate_limited(request): return {"error":"Too many requests. Please wait a minute and try again."}
    try:
        client=requests.Session(); parsed=_get_form(client)
        if not parsed: return {"error":"NU Masters result form could not be read."}
        csrf,action,question=parsed
        return {"captcha":question,"session":seal({"csrf":csrf,"cookies":client.cookies.get_dict(),"action":action,"module":"masters"}),"expires_in":300}
    except RuntimeError: return {"error":"Server security configuration is incomplete."}
    except requests.RequestException: return {"error":"Could not connect to the NU Masters result server."}

@app.get("/api/masters")
def masters_get(request: Request, action: str="examinations"):
    if action=="examinations": return {"examinations":MASTERS_EXAMINATIONS}
    if action=="captcha": return _captcha(request)
    return {"error":"Unsupported Masters API action."}

@app.post("/api/masters")
def masters_result(body: dict[str,Any], request: Request):
    if rate_limited(request): return {"found":False,"message":"Too many searches. Please wait a minute and try again."}
    exam=str(body.get("examination_name",""))
    if exam not in MASTERS_EXAMINATIONS: return {"found":False,"message":"Unsupported Masters examination type."}
    try:
        state=unseal(str(body.get("session","")))
        if state.get("module")!="masters": raise ValueError("wrong module")
        csrf=state.get("csrf"); action=state.get("action"); cookies=state.get("cookies") or {}
        if not csrf or not action: raise ValueError("missing session")
        client=requests.Session(); client.cookies.update(cookies)
        headers={**HTML_HEADERS,"Referer":MASTERS_URL,"Origin":"https://results.nu.ac.bd","Content-Type":"application/x-www-form-urlencoded"}
        r=client.post(str(action),headers=headers,data={"_token":csrf,"examination_name":exam,"year":str(body.get("year","")),"examination_roll":str(body.get("examination_roll","")),"registration_no":str(body.get("registration_no","")),"captcha":str(body.get("captcha",""))},timeout=28,allow_redirects=True)
        r.raise_for_status(); parsed=parse_masters_result(r.text)
        return parsed if parsed.get("found") else {"found":False,"message":"Result was not found. Check your details and CAPTCHA."}
    except ValueError: return {"found":False,"message":"Search session is invalid or expired. Please refresh the CAPTCHA."}
    except RuntimeError: return {"found":False,"message":"Server security configuration is incomplete."}
    except requests.RequestException: return {"found":False,"message":"NU Masters result server is taking too long to respond. Please try again without changing your CAPTCHA."}

__all__=["MASTERS_CAPTCHA_REFRESH_URL","MASTERS_EXAMINATIONS","MASTERS_URL","parse_masters_result"]
