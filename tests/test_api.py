import os
import unittest

os.environ.setdefault("SESSION_SIGNING_SECRET", "ci-test-secret")

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
        self.assertEqual(result["summary"]["gpa"], 3.63)

    def test_non_result_page_is_not_reported_as_found(self):
        result = parse_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
