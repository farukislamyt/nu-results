import os
import unittest

os.environ.setdefault("SESSION_SIGNING_SECRET", "ci-test-secret")

from api.degree import parse_degree_result
from api.index import EXAMINATIONS, grade_point, parse_result, seal, unseal


class ApiRegressionTests(unittest.TestCase):
    def test_exam_catalog_is_complete(self):
        self.assertEqual(set(EXAMINATIONS), {"2201", "2202", "2203", "2204", "2205"})

    def test_grade_points(self):
        self.assertEqual(grade_point("A+"), 4.0)
        self.assertEqual(grade_point(" a- "), 3.5)
        self.assertEqual(grade_point("F"), 0.0)
        self.assertIsNone(grade_point("X"))

    def test_session_is_encrypted_and_round_trips(self):
        token = seal({"csrf": "csrf-value", "cookies": {"session": "cookie-value"}})
        self.assertNotIn("csrf-value", token)
        self.assertEqual(unseal(token)["csrf"], "csrf-value")

    def test_result_parser_and_weighted_gpa(self):
        html = """
        <html><body>
          <div class="p-3 rounded-3 bg-light"><span class="text-muted">Name of Student</span> Test Student</div>
          <div class="p-3 rounded-3 bg-light"><span class="text-muted">College</span> Test College</div>
          <table><thead><tr><th>Course Code</th><th>Title of Course</th><th>Credit</th><th>Letter Grade</th></tr></thead>
          <tbody>
            <tr><td>101</td><td>Course One</td><td>3</td><td>A</td></tr>
            <tr><td>102</td><td>Course Two</td><td>1</td><td>B+</td></tr>
          </tbody></table>
          <div>ONLINE RESULT SHEET</div>
        </body></html>
        """
        result = parse_result(html)
        self.assertTrue(result["found"])
        self.assertEqual(len(result["courses"]), 2)
        self.assertEqual(result["summary"]["total_credit"], 4.0)
        self.assertEqual(result["summary"]["gpa"], 3.62)

    def test_degree_parser_matches_current_nu_result_structure(self):
        html = """
        <html><body>
          <div class="result-card">
            <h5>National University, Bangladesh</h5>
            <p>Bachelor Degree Pass &amp; Certificate Course 1st Year Examination — 2023</p>
            <span>ONLINE RESULT SHEET</span>
            <div><span>Examination Roll</span><span>3264222</span></div>
            <div><span>Registration No.</span><span>22101231320</span></div>
            <div><span>Name of Student</span><span>TEST STUDENT</span></div>
            <div><span>Father's Name</span><span>TEST FATHER</span></div>
            <div><span>Mother's Name</span><span>TEST MOTHER</span></div>
            <div><span>College</span><span>(6485) TEST COLLEGE</span></div>
            <div><span>Session</span><span>2022-23</span></div>
            <div><span>Student Type</span><span>Regular</span></div>
            <div><span>Course</span><span>B.A</span></div>
            <div><span>Result</span><span>Promoted</span></div>
            <table><thead><tr><th>Course Code</th><th>Title of Course</th><th>Marks/Grade</th></tr></thead>
              <tbody>
                <tr><td>111501</td><td>HISTORY OF BANGLADESH</td><td>C</td></tr>
                <tr><td>111901</td><td>POLITICAL THEORY</td><td>F</td></tr>
              </tbody>
            </table>
            <div>Result Upload Date: 09 Jul 2026</div>
            <div>Generated on 13 Sep 2026 by National University</div>
          </div>
        </body></html>
        """
        result = parse_degree_result(html)
        self.assertTrue(result["found"])
        self.assertEqual(result["result_title"], "Bachelor Degree Pass & Certificate Course 1st Year Examination — 2023")
        self.assertEqual(result["student"]["examination_roll"], "3264222")
        self.assertEqual(result["student"]["registration_no"], "22101231320")
        self.assertEqual(result["student"]["name"], "TEST STUDENT")
        self.assertEqual(result["student"]["college"], "(6485) TEST COLLEGE")
        self.assertEqual(result["result_status"], "Promoted")
        self.assertEqual(result["course_result_label"], "Marks/Grade")
        self.assertEqual(result["summary"]["total_courses"], 2)
        self.assertIsNone(result["summary"]["gpa"])
        self.assertEqual(result["dates"]["result_upload_date"], "09 Jul 2026")
        self.assertEqual(result["dates"]["generated_on"], "13 Sep 2026")

    def test_degree_parser_accepts_gpa_and_old_roll_name_labels(self):
        html = """
        <html><body>
          <div>National University, Bangladesh</div>
          <div>Degree Pass &amp; Certificate Course 2nd Year Examination - 2024</div>
          <div>ONLINE RESULT SHEET</div>
          <div><span>Roll No.</span><span>4091253</span></div>
          <div><span>Registration No.</span><span>22102111125</span></div>
          <div><span>Student's Name</span><span>TEST STUDENT</span></div>
          <div><span>Result</span><span>Promoted</span></div>
          <div>GPA 2.68</div>
          <table><tr><th>Course Code</th><th>Course Title</th><th>Ltr. Grade</th></tr>
            <tr><td>131001</td><td>BANGLA NATIONAL LANGUAGE</td><td>D</td></tr>
          </table>
        </body></html>
        """
        result = parse_degree_result(html)
        self.assertTrue(result["found"])
        self.assertEqual(result["student"]["examination_roll"], "4091253")
        self.assertEqual(result["student"]["name"], "TEST STUDENT")
        self.assertEqual(result["gpa"], 2.68)
        self.assertEqual(result["summary"]["gpa"], 2.68)
        self.assertEqual(result["courses"][0]["result"], "D")

    def test_non_result_page_is_not_reported_as_found(self):
        result = parse_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(result["found"])
        degree_result = parse_degree_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(degree_result["found"])


if __name__ == "__main__":
    unittest.main()
