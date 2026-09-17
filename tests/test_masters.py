import unittest

import requests

from api.masters import MASTERS_EXAMINATIONS, _form_from_response, parse_masters_result


FORM_HTML = """
<form method="POST" action="https://results.nu.ac.bd/pageaI20PRYeyVg6uoxEygIC0j6ZtXgaOScAjmXhuevii">
  <input type="hidden" name="_token" value="wfTNO6tJPmlE51MetuTMHOoKiqkI1Yo2ZKEgUu5g">
  <select name="examination_name">
    <option value="3302">Masters Final Result (Available from 2007)</option>
    <option value="4301">Preliminary to Master's Result (Available from 2005)</option>
    <option value="3303">ICT Course Result (Available from 2020)</option>
  </select>
  <span class="fw-bold fs-5">6 + 3 =</span>
</form>
"""


MASTERS_FINAL_HTML = """
<div id="result-section">
  <div class="card-header"><h5>National University, Bangladesh</h5><p>Masters Final Examination — 2021</p><span>ONLINE RESULT SHEET</span></div>
  <div class="card-body">
    <div><span>Examination Roll</span><span>2152253</span></div>
    <div><span>Registration No.</span><div class="d-flex"><span>2</span><span>0</span><span>3</span><span>2</span><span>5</span><span>1</span><span>1</span><span>9</span><span>9</span><span>5</span><span>0</span></div></div>
    <div><span>Name of Student</span><span>FATEMA AKTER BITHE</span></div>
    <div><span>Father's Name</span><span>MOHAMMAD ALI DALI</span></div>
    <div><span>Mother's Name</span><span>MAZEDA BEGUM</span></div>
    <div><span>College</span><span>(5601) GOVT. TOLARAM COLLEGE, NARAYANGANJ</span></div>
    <div><span>Session</span><span>20-21</span></div>
    <div><span>Student Type</span><span>Regular</span></div>
    <div><span>Subject</span><span>25 — ACCOUNTING</span></div>
    <div><span>CGPA</span><div>2.92</div></div>
    <table><thead><tr><th>Course Code</th><th>Title of Course</th><th>Credit</th><th>Letter Grade</th></tr></thead><tbody>
      <tr><td>312501</td><td>APPLIED ACCOUNTING THEORY :6201</td><td>4</td><td>B-</td></tr>
      <tr><td>312503</td><td>ADVANCED COST ACCOUNTING</td><td>4</td><td>C+</td></tr>
      <tr><td>312505</td><td>STRATEGIC MANAGEMENT ACCOUNTING</td><td>4</td><td>B</td></tr>
      <tr><td>312507</td><td>STRATEGIC MANAGEMENT</td><td>4</td><td>C+</td></tr>
      <tr><td>312509</td><td>CORPORATE GOVERNANCE</td><td>4</td><td>B-</td></tr>
      <tr><td>312511</td><td>CORPORATE FINANCIAL REPORTING</td><td>4</td><td>B-</td></tr>
      <tr><td>312513</td><td>CORPORATE TAX PLANNING</td><td>4</td><td>B+</td></tr>
      <tr><td>312514</td><td>TERM PAPER</td><td>2</td><td>A+</td></tr>
      <tr><td>312516</td><td>VIVA-VOCE</td><td>2</td><td>A</td></tr>
    </tbody></table>
    <div>Result Upload Date: 29 Apr 2026</div>
    <div>Generated on 17 Sep 2026 by National University</div>
  </div>
</div>
"""


PRELIMINARY_HTML = """
<div id="result-section">
  <div class="card-header"><h5>National University, Bangladesh</h5><p>Masters Preliminary Examination — 2022</p><span>ONLINE RESULT SHEET</span></div>
  <div class="card-body">
    <div><span>Examination Roll</span><span>2000586</span></div>
    <div><span>Registration No.</span><div class="d-flex"><span>2</span><span>1</span><span>4</span><span>1</span><span>6</span><span>0</span><span>0</span><span>0</span><span>2</span><span>9</span><span>9</span></div></div>
    <div><span>Name of Student</span><span>NURZAHAN KHATUN</span></div>
    <div><span>Father's Name</span><span>MD. JIHAD GOLDER</span></div>
    <div><span>Mother's Name</span><span>AKTARA BEGUM</span></div>
    <div><span>College</span><span>(0322) GOVT. B. L. COLLEGE, KHULNA</span></div>
    <div><span>Session</span><span>2021-22</span></div>
    <div><span>Student Type</span><span>Regular</span></div>
    <div><span>Subject</span><span>16 — ISLAMIC HISTORY &amp; CULTURE</span></div>
    <div><span>CGPA</span><div>3.28</div></div>
    <table><thead><tr><th>Course Code</th><th>Title of Course</th><th>Credit</th><th>Letter Grade</th></tr></thead><tbody>
      <tr><td>411601</td><td>History of The Muslim Rule In North Africa And Spain (7...</td><td>4</td><td>B-</td></tr>
      <tr><td>411603</td><td>Development of Muslim Administration (prophet (s), Khul...</td><td>4</td><td>B+</td></tr>
      <tr><td>411605</td><td>Muslim Administration In India (sultanat And Mugal)</td><td>4</td><td>B</td></tr>
      <tr><td>411607</td><td>Development of Muslim Art And Architecture</td><td>4</td><td>A</td></tr>
      <tr><td>411609</td><td>History of Ancient And Medieval Civilizations</td><td>4</td><td>B</td></tr>
      <tr><td>411611</td><td>History of The Middle East</td><td>4</td><td>A-</td></tr>
      <tr><td>411613</td><td>Development of Muslim Historiography</td><td>4</td><td>B</td></tr>
      <tr><td>411615</td><td>History of The Muslims In Bengal (1200-1765)</td><td>4</td><td>B+</td></tr>
      <tr><td>411618</td><td>Viva-voce</td><td>4</td><td>A+</td></tr>
    </tbody></table>
    <div>Result Upload Date: 29 Apr 2026</div>
  </div>
</div>
"""


ICT_HTML = """
<div id="result-section">
  <div class="card-header"><h5>National University, Bangladesh</h5><p>ICT Course Examination — 2022</p><span>ONLINE RESULT SHEET</span></div>
  <div class="card-body">
    <div><span>Examination Roll</span><span>2321522</span></div>
    <div><span>Registration No.</span><div class="d-flex"><span>2</span><span>1</span><span>3</span><span>3</span><span>7</span><span>0</span><span>8</span><span>4</span><span>6</span><span>4</span><span>0</span></div></div>
    <div><span>Name of Student</span><span>MD DOULAT HOSSAIN</span></div>
    <div><span>Father's Name</span><span>MD SIRAJUL HOQUE</span></div>
    <div><span>Mother's Name</span><span>PARVIN AKTER</span></div>
    <div><span>College</span><span>(4301) CHITTAGONG COLLEGE, CHATTOGRAM</span></div>
    <div><span>Session</span><span>2021-202</span></div>
    <div><span>Student Type</span><span>—</span></div>
    <div><span>Subject</span><span>37 — MATHEMATICS</span></div>
    <div><span>GPA</span><div>3.25</div></div>
    <div>Result Upload Date: 14 May 2026</div>
  </div>
</div>
"""


class MastersParserTests(unittest.TestCase):
    def test_exam_catalog_matches_official_form(self):
        self.assertEqual(
            MASTERS_EXAMINATIONS,
            {
                "3302": "Masters Final Result (Available from 2007)",
                "4301": "Preliminary to Master's Result (Available from 2005)",
                "3303": "ICT Course Result (Available from 2020)",
            },
        )

    def test_dynamic_form_extracts_token_action_and_captcha(self):
        response = requests.Response()
        response.status_code = 200
        response.url = "https://results.nu.ac.bd/masters"
        response._content = FORM_HTML.encode()
        parsed = _form_from_response(response)
        self.assertIsNotNone(parsed)
        csrf, action, captcha = parsed
        self.assertEqual(csrf, "wfTNO6tJPmlE51MetuTMHOoKiqkI1Yo2ZKEgUu5g")
        self.assertEqual(action, "https://results.nu.ac.bd/pageaI20PRYeyVg6uoxEygIC0j6ZtXgaOScAjmXhuevii")
        self.assertEqual(captcha, "6 + 3 =")

    def test_masters_final_3302(self):
        result = parse_masters_result(MASTERS_FINAL_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["examination_name"], "3302")
        self.assertEqual(result["result_metric"], "CGPA")
        self.assertEqual(result["cgpa"], 2.92)
        self.assertIsNone(result["gpa"])
        self.assertEqual(result["student"]["registration_no"], "20325119950")
        self.assertEqual(len(result["courses"]), 9)
        self.assertEqual(result["summary"]["total_credit"], 32.0)
        self.assertEqual(result["summary"]["calculated_gpa"], 2.92)
        self.assertEqual(result["dates"]["result_upload_date"], "29 Apr 2026")

    def test_preliminary_4301(self):
        result = parse_masters_result(PRELIMINARY_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["examination_name"], "4301")
        self.assertEqual(result["result_metric"], "CGPA")
        self.assertEqual(result["cgpa"], 3.28)
        self.assertIsNone(result["gpa"])
        self.assertEqual(result["student"]["name"], "NURZAHAN KHATUN")
        self.assertEqual(result["student"]["subject"], "16 — ISLAMIC HISTORY & CULTURE")
        self.assertEqual(len(result["courses"]), 9)

    def test_ict_3303_has_official_gpa_and_no_courses(self):
        result = parse_masters_result(ICT_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["examination_name"], "3303")
        self.assertEqual(result["result_metric"], "GPA")
        self.assertEqual(result["gpa"], 3.25)
        self.assertIsNone(result["cgpa"])
        self.assertEqual(result["courses"], [])
        self.assertEqual(result["summary"]["total_courses"], 0)
        self.assertIsNone(result["summary"]["calculated_gpa"])
        self.assertEqual(result["student"]["student_type"], "—")

    def test_cgpa_is_not_mistaken_for_gpa(self):
        result = parse_masters_result(MASTERS_FINAL_HTML)
        self.assertEqual(result["cgpa"], 2.92)
        self.assertIsNone(result["gpa"])

    def test_non_result_page(self):
        self.assertFalse(parse_masters_result("<html><body>Invalid CAPTCHA</body></html>")["found"])

    def test_malformed_result_page_is_not_success(self):
        html = "<div id='result-section'><h5>National University, Bangladesh</h5><p>Masters Final Examination — 2021</p><span>ONLINE RESULT SHEET</span></div>"
        self.assertFalse(parse_masters_result(html)["found"])


if __name__ == "__main__":
    unittest.main()
