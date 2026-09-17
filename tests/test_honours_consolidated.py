import unittest
from pathlib import Path

from api.honours import parse_result


class HonoursConsolidatedParserTests(unittest.TestCase):
    def test_consolidated_official_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "honours_consolidated.html"
        result = parse_result(fixture.read_text(encoding="utf-8"), "2205")
        self.assertTrue(result["found"])
        self.assertEqual(len(result["courses"]), 8)
        self.assertEqual(result["courses"][0]["course_code"], "211501")
        self.assertEqual(result["courses"][0]["credit"], 4)
        self.assertEqual(result["courses"][0]["year"], "First Year")
        self.assertEqual(result["summary"]["total_credit"], 32.0)
        self.assertEqual(result["summary"]["yearly_gpa"]["First Year"], 2.67)
        self.assertEqual(result["summary"]["yearly_gpa"]["Fourth Year"], 2.40)
        self.assertEqual(result["summary"]["official_cgpa"], 2.52)


if __name__ == "__main__":
    unittest.main()
