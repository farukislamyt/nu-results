import unittest
from unittest.mock import patch

from api.masters import MASTERS_EXAMINATIONS, _captcha_response, parse_masters_result

REAL_MASTERS_FINAL_HTML = """
<html><body>
  <div class="container">
    <form method="POST" action="https://results.nu.ac.bd/pageexample">
      <input type="hidden" name="_token" value="token">
      <select name="examination_name">
        <option value="3302" selected>Masters Final Result (Available from 2007)</option>
        <option value="4301">Preliminary to Master's Result (Available from 2005)</option>
        <option value="3303">ICT Course Result (Available from 2020)</option>
      </select>
      <input name="year" value="2021">
      <input name="examination_roll" value="2148697">
      <input name="registration_no" value="20321117322">
      <input name="captcha" value="">
    </form>
    <div id="result-section">
      <h5>National University, Bangladesh</h5>
      <p>Masters Final Examination — 2021</p>
      <span>ONLINE RESULT SHEET</span>
      <div><span>Examination Roll</span><span>2148697</span></div>
      <div><span>Registration No.</span><div>2 0 3 2 1 1 1 7 3 2 2</div></div>
      <div><span>Name of Student</span><span>PAKHY AKTHER</span></div>
      <div><span>Father's Name</span><span>MD. FAZLUL HAQUE</span></div>
      <div><span>Mother's Name</span><span>MRS. ROKEYA BEGUM</span></div>
      <div><span>College</span><span>(5511) TONGI GOVT. COLLEGE, GAZIPUR</span></div>
      <div><span>Session</span><span>20-21</span></div>
      <div><span>Student Type</span><span>Regular</span></div>
      <div><span>Subject</span><span>21 — SOCIAL WORK</span></div>
      <div><span>CGPA</span><div>2.50</div></div>
      <h6>Course-wise Grade / Marks</h6>
      <table>
        <thead><tr><th>Course Code</th><th>Title of Course</th><th>Credit</th><th>Letter Grade</th></tr></thead>
        <tbody>
          <tr><td>312101</td><td>SOCIAL ADMINISTRATION</td><td>4</td><td>B-</td></tr>
          <tr><td>312103</td><td>ADVANCED SOCIAL RESEARCH AND STATISTICS</td><td>4</td><td>D</td></tr>
          <tr><td>312105</td><td>INDUSTRIAL RELATIONS AND LABOUR LAWS</td><td>4</td><td>C+</td></tr>
          <tr><td>312107</td><td>CORRECTION AND CORRECTIONAL SERVICES</td><td>4</td><td>D</td></tr>
          <tr><td>312109</td><td>WOMEN AND FAMILY WELFARE</td><td>4</td><td>B</td></tr>
          <tr><td>312111</td><td>WELFARE FOR THE CHILD YOUTH AND OLDER PERSONS</td><td>4</td><td>B</td></tr>
          <tr><td>312113</td><td>GUIDANCE AND COUNSELING IN SOCIAL WORK</td><td>4</td><td>B-</td></tr>
          <tr><td>312114</td><td>FIELD PRACTICUM &amp; VIVA-VOCE</td><td>4</td><td>D</td></tr>
        </tbody>
      </table>
      <div><b>Result Upload Date:</b> 29 Apr 2026</div>
      <div>Generated on 15 Sep 2026 by National University</div>
    </div>
  </div>
</body></html>
"""

SEARCH_HTML = """
<html><body>
<form method="POST" action="https://results.nu.ac.bd/pageABC123">
<input type="hidden" name="_token" value="CSRF123">
<select name="examination_name"><option value="3302">Masters Final</option></select>
<span class="fw-bold fs-5">9 + 1 =</span>
<input name="captcha">
</form>
</body></html>
"""


class MastersParserTests(unittest.TestCase):
    def test_exam_catalog_matches_nu(self):
        self.assertEqual(
            MASTERS_EXAMINATIONS,
            {
                "3302": "Masters Final Result (Available from 2007)",
                "4301": "Preliminary to Master's Result (Available from 2005)",
                "3303": "ICT Course Result (Available from 2020)",
            },
        )

    def test_real_masters_final_result_structure(self):
        result = parse_masters_result(REAL_MASTERS_FINAL_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["result_title"], "Masters Final Examination — 2021")
        self.assertEqual(result["student"]["name"], "PAKHY AKTHER")
        self.assertEqual(result["student"]["examination_roll"], "2148697")
        self.assertEqual(result["student"]["registration_no"], "2 0 3 2 1 1 1 7 3 2 2")
        self.assertEqual(result["student"]["college"], "(5511) TONGI GOVT. COLLEGE, GAZIPUR")
        self.assertEqual(result["student"]["session"], "20-21")
        self.assertEqual(result["student"]["student_type"], "Regular")
        self.assertEqual(result["student"]["subject"], "21 — SOCIAL WORK")
        self.assertEqual(result["cgpa"], 2.50)
        self.assertIsNone(result["gpa"])
        self.assertEqual(len(result["courses"]), 8)
        self.assertEqual(result["courses"][0]["grade"], "B-")
        self.assertEqual(result["courses"][-1]["course_code"], "312114")
        self.assertEqual(result["summary"]["total_credit"], 32.0)
        self.assertEqual(result["summary"]["calculated_gpa"], 2.5)
        self.assertEqual(result["dates"]["result_upload_date"], "29 Apr 2026")
        self.assertEqual(result["dates"]["generated_on"], "15 Sep 2026 by National University")

    def test_cgpa_is_not_mistaken_for_gpa(self):
        result = parse_masters_result(REAL_MASTERS_FINAL_HTML)
        self.assertEqual(result["cgpa"], 2.50)
        self.assertIsNone(result["gpa"])

    @patch("api.masters.rate_limited", return_value=False)
    @patch("api.masters.requests.Session")
    def test_captcha_reads_dynamic_form_action(self, session_cls, _rate_limited):
        session = session_cls.return_value
        session.get.return_value.text = SEARCH_HTML
        session.get.return_value.raise_for_status.return_value = None
        session.cookies.get_dict.return_value = {"laravel_session": "abc"}
        result = _captcha_response(object())
        self.assertEqual(result["captcha"], "9 + 1 =")
        state = result["session"]
        self.assertTrue(state)
        session.get.assert_called_once()

    def test_non_result_page(self):
        result = parse_masters_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
