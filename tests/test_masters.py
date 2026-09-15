import unittest

from api.masters import MASTERS_EXAMINATIONS, parse_masters_result


class MastersParserTests(unittest.TestCase):
    def test_exam_catalog(self):
        self.assertEqual(MASTERS_EXAMINATIONS, {"3301": "Preliminary to Masters", "3302": "Masters Final"})

    def test_masters_final_result_structure(self):
        html = """
        <html><body>
          <h2>National University, Bangladesh</h2>
          <p>Masters Final Examination-2022</p>
          <div>Result Sheet</div>
          <table>
            <tr><td>Name of Student</td><td>TAPOS CHANDRO</td></tr>
            <tr><td>Father's Name</td><td>POLIN CHANDRO</td></tr>
            <tr><td>Mother's Name</td><td>DHOULI BALA</td></tr>
            <tr><td>Name of College</td><td>[3101] NILPHAMARI GOVT. COLLEGE</td></tr>
            <tr><td>Exam. Roll</td><td>2281499</td></tr>
            <tr><td>Registration</td><td>20326063576</td></tr>
            <tr><td>Session</td><td>20-21</td></tr>
            <tr><td>Student Type</td><td>Irregular</td></tr>
            <tr><td>Subject Name</td><td>[26] MANAGEMENT</td></tr>
            <tr><td>CGPA</td><td>2.58</td></tr>
          </table>
          <table>
            <thead><tr><th>Course Code</th><th>Course Title</th><th>Credit</th><th>Letter Grade</th></tr></thead>
            <tbody>
              <tr><td>312601</td><td>MANAGEMENT THOUGHT</td><td>4</td><td>D</td></tr>
              <tr><td>312603</td><td>INTERNATIONAL BUSINESS</td><td>4</td><td>C+</td></tr>
              <tr><td>312605</td><td>BUSINESS RESEARCH</td><td>4</td><td>B</td></tr>
              <tr><td>312614</td><td>TERM PAPER</td><td>2</td><td>A</td></tr>
            </tbody>
          </table>
        </body></html>
        """
        result = parse_masters_result(html)
        self.assertTrue(result["found"])
        self.assertEqual(result["student"]["name"], "TAPOS CHANDRO")
        self.assertEqual(result["student"]["examination_roll"], "2281499")
        self.assertEqual(result["student"]["registration_no"], "20326063576")
        self.assertEqual(result["student"]["college"], "[3101] NILPHAMARI GOVT. COLLEGE")
        self.assertEqual(result["student"]["subject"], "[26] MANAGEMENT")
        self.assertEqual(result["cgpa"], 2.58)
        self.assertEqual(len(result["courses"]), 4)
        self.assertEqual(result["courses"][0]["grade"], "D")
        self.assertEqual(result["summary"]["total_credit"], 14.0)
        self.assertEqual(result["summary"]["calculated_gpa"], 2.79)

    def test_non_result_page(self):
        result = parse_masters_result("<html><body>Invalid CAPTCHA</body></html>")
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
