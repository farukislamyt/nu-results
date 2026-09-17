import unittest

from api.masters import MASTERS_EXAMINATIONS, parse_masters_result


OFFICIAL_MASTERS_FINAL_HTML = """
<!DOCTYPE html><html lang="en"><body>
  <form method="POST" action="https://results.nu.ac.bd/pageexample">
    <input type="hidden" name="_token" value="official-token">
    <select name="examination_name">
      <option value="3302" selected>Masters Final Result (Available from 2007)</option>
      <option value="4301">Preliminary to Master's Result (Available from 2005)</option>
      <option value="3303">ICT Course Result (Available from 2020)</option>
    </select>
    <input name="year" value="2021">
    <input name="examination_roll" value="2152253">
    <input name="registration_no" value="20325119950">
    <span class="fw-bold fs-5">8 + 1 =</span>
  </form>
  <div id="result-section">
    <div class="card-header">
      <h5>National University, Bangladesh</h5>
      <p>Masters Final Examination — 2021</p>
      <span class="badge">ONLINE RESULT SHEET</span>
    </div>
    <div class="card-body">
      <div><span>Examination Roll</span><span>2152253</span></div>
      <div><span>Registration No.</span><div class="d-flex">
        <span>2</span><span>0</span><span>3</span><span>2</span><span>5</span><span>1</span><span>1</span><span>9</span><span>9</span><span>5</span><span>0</span>
      </div></div>
      <div><span>Name of Student</span><span>FATEMA AKTER BITHE</span></div>
      <div><span>Father's Name</span><span>MOHAMMAD ALI DALI</span></div>
      <div><span>Mother's Name</span><span>MAZEDA BEGUM</span></div>
      <div><span>College</span><span>(5601) GOVT. TOLARAM COLLEGE, NARAYANGANJ</span></div>
      <div><span>Session</span><span>20-21</span></div>
      <div><span>Student Type</span><span>Regular</span></div>
      <div><span>Subject</span><span>25 — ACCOUNTING</span></div>
      <div><span>CGPA</span><div>2.92</div></div>
      <h6>Course-wise Grade / Marks</h6>
      <table>
        <thead><tr><th>Course Code</th><th>Title of Course</th><th>Credit</th><th>Letter Grade</th></tr></thead>
        <tbody>
          <tr><td>312501</td><td>APPLIED ACCOUNTING THEORY :6201</td><td>4</td><td>B-</td></tr>
          <tr><td>312503</td><td>ADVANCED COST ACCOUNTING</td><td>4</td><td>C+</td></tr>
          <tr><td>312505</td><td>STRATEGIC MANAGEMENT ACCOUNTING</td><td>4</td><td>B</td></tr>
          <tr><td>312507</td><td>STRATEGIC MANAGEMENT</td><td>4</td><td>C+</td></tr>
          <tr><td>312509</td><td>CORPORATE GOVERNANCE</td><td>4</td><td>B-</td></tr>
          <tr><td>312511</td><td>CORPORATE FINANCIAL REPORTING</td><td>4</td><td>B-</td></tr>
          <tr><td>312513</td><td>CORPORATE TAX PLANNING</td><td>4</td><td>B+</td></tr>
          <tr><td>312514</td><td>TERM PAPER</td><td>2</td><td>A+</td></tr>
          <tr><td>312516</td><td>VIVA-VOCE</td><td>2</td><td>A</td></tr>
        </tbody>
      </table>
      <div><b>Result Upload Date:</b> 29 Apr 2026</div>
      <div>Generated on 17 Sep 2026 by National University</div>
    </div>
  </div>
</body></html>
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

    def test_official_masters_final_result_structure(self):
        result = parse_masters_result(OFFICIAL_MASTERS_FINAL_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["result_title"], "Masters Final Examination — 2021")
        self.assertEqual(result["student"]["name"], "FATEMA AKTER BITHE")
        self.assertEqual(result["student"]["examination_roll"], "2152253")
        self.assertEqual(result["student"]["registration_no"], "20325119950")
        self.assertEqual(result["student"]["father"], "MOHAMMAD ALI DALI")
        self.assertEqual(result["student"]["mother"], "MAZEDA BEGUM")
        self.assertEqual(result["student"]["college"], "(5601) GOVT. TOLARAM COLLEGE, NARAYANGANJ")
        self.assertEqual(result["student"]["session"], "20-21")
        self.assertEqual(result["student"]["student_type"], "Regular")
        self.assertEqual(result["student"]["subject"], "25 — ACCOUNTING")
        self.assertEqual(result["cgpa"], 2.92)
        self.assertIsNone(result["gpa"])
        self.assertEqual(len(result["courses"]), 9)
        self.assertEqual(result["courses"][0], {
            "course_code": "312501",
            "course_title": "APPLIED ACCOUNTING THEORY :6201",
            "credit": "4",
            "grade": "B-",
            "result": "B-",
        })
        self.assertEqual(result["courses"][-1]["course_code"], "312516")
        self.assertEqual(result["courses"][-1]["credit"], "2")
        self.assertEqual(result["courses"][-1]["grade"], "A")
        self.assertEqual(result["summary"]["total_credit"], 32.0)
        self.assertEqual(result["summary"]["calculated_gpa"], 2.92)
        self.assertEqual(result["dates"]["result_upload_date"], "29 Apr 2026")
        self.assertEqual(result["dates"]["generated_on"], "17 Sep 2026 by National University")

    def test_cgpa_is_not_mistaken_for_gpa(self):
        result = parse_masters_result(OFFICIAL_MASTERS_FINAL_HTML)
        self.assertEqual(result["cgpa"], 2.92)
        self.assertIsNone(result["gpa"])

    def test_registration_digits_are_normalized(self):
        html = OFFICIAL_MASTERS_FINAL_HTML.replace(
            '<div class="d-flex">\n        <span>2</span><span>0</span><span>3</span><span>2</span><span>5</span><span>1</span><span>1</span><span>9</span><span>9</span><span>5</span><span>0</span>\n      </div>',
            '<div class="d-flex"><span>2</span> <span>0</span> <span>3</span> <span>2</span> <span>5</span> <span>1</span> <span>1</span> <span>9</span> <span>9</span> <span>5</span> <span>0</span></div>',
        )
        result = parse_masters_result(html)
        self.assertEqual(result["student"]["registration_no"], "20325119950")

    def test_non_result_page(self):
        result = parse_masters_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(result["found"])

    def test_malformed_result_page_is_not_success(self):
        html = """
        <div id="result-section">
          <h5>National University, Bangladesh</h5>
          <p>Masters Final Examination — 2021</p>
          <span>ONLINE RESULT SHEET</span>
        </div>
        """
        result = parse_masters_result(html)
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
