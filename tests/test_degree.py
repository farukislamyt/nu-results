import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from degree import DEGREE_EXAMINATIONS, parse_degree_result


SAMPLE = """
<html><body>
<div>National University Bangladesh</div>
<div> Bachelor Degree Pass &amp; Certificate Course 1st Year Examination - 2023 </div>
<div>ONLINE RESULT SHEET</div>
<table><tr><td>Examination Roll</td><td>123456</td></tr>
<tr><td>Registration No.</td><td>987654</td></tr>
<tr><td>Name</td><td>Test Student</td></tr>
<tr><td>Father's Name</td><td>Test Father</td></tr>
<tr><td>Mother's Name</td><td>Test Mother</td></tr>
<tr><td>College</td><td>Test College</td></tr>
<tr><td>Session</td><td>2021-22</td></tr>
<tr><td>Student Type</td><td>Regular</td></tr>
<tr><td>Course</td><td>Degree Pass</td></tr>
<tr><td>Result</td><td>Promoted</td></tr></table>
<table><thead><tr><th>Course Code</th><th>Title of Course</th><th>Marks/Grade</th></tr></thead>
<tbody><tr><td>110101</td><td>Bangla</td><td>A</td></tr>
<tr><td>110102</td><td>English</td><td>B+</td></tr></tbody></table>
<div>Result Upload Date: 15/06/2026</div>
<div>Generated on: 13/09/2026</div>
</body></html>
"""


class DegreeTests(unittest.TestCase):
    def test_exam_catalog_is_complete(self):
        self.assertEqual(set(DEGREE_EXAMINATIONS), {"1101", "1102", "1103", "1104"})

    def test_parser_extracts_student_and_status(self):
        parsed = parse_degree_result(SAMPLE)
        self.assertTrue(parsed["found"])
        self.assertEqual(parsed["student"]["name"], "Test Student")
        self.assertEqual(parsed["student"]["registration_no"], "987654")
        self.assertEqual(parsed["result_status"], "Promoted")

    def test_parser_extracts_courses_without_gpa(self):
        parsed = parse_degree_result(SAMPLE)
        self.assertEqual(len(parsed["courses"]), 2)
        self.assertEqual(parsed["courses"][0]["course_code"], "110101")
        self.assertEqual(parsed["courses"][1]["result"], "B+")
        self.assertNotIn("gpa", parsed["summary"])

    def test_non_result_page_is_not_reported_as_found(self):
        parsed = parse_degree_result("<html><body>Degree result search form</body></html>")
        self.assertFalse(parsed["found"])


if __name__ == "__main__":
    unittest.main()
