import unittest

from api.honours import parse_result


class HonoursConsolidatedParserTests(unittest.TestCase):
    def test_consolidated_nested_year_tables(self):
        html = """
        <html><body>
          <div>ONLINE RESULT SHEET</div>
          <div class="p-3 rounded-3 bg-light">
            <span class="text-muted">Name of Student</span> Test Student
          </div>
          <div class="cgpa-box"><span>CGPA</span><span>2.52</span></div>
          <table>
            <thead>
              <tr><th>First Year</th><th>Second Year</th><th>Third Year</th><th>Fourth Year</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><table><thead><tr><th>Course Code</th><th>LG</th></tr></thead><tbody>
                  <tr><td>211501(04)</td><td>B-</td></tr>
                  <tr><td>211701(04)</td><td>C+</td></tr>
                </tbody></table></td>
                <td><table><thead><tr><th>Course Code</th><th>LG</th></tr></thead><tbody>
                  <tr><td>221701(04)</td><td>B-</td></tr>
                  <tr><td>221703(04)</td><td>B</td></tr>
                </tbody></table></td>
                <td><table><thead><tr><th>Course Code</th><th>LG</th></tr></thead><tbody>
                  <tr><td>231701(04)</td><td>C</td></tr>
                  <tr><td>231703(04)</td><td>C+</td></tr>
                </tbody></table></td>
                <td><table><thead><tr><th>Course Code</th><th>LG</th></tr></thead><tbody>
                  <tr><td>241701(04)</td><td>D</td></tr>
                  <tr><td>241703(04)</td><td>C</td></tr>
                </tbody></table></td>
              </tr>
            </tbody>
            <thead>
              <tr><td>GPA: 2.67</td><td>GPA: 2.58</td><td>GPA: 2.50</td><td>GPA: 2.40</td></tr>
            </thead>
          </table>
        </body></html>
        """
        result = parse_result(html, "2205")
        self.assertTrue(result["found"])
        self.assertEqual(len(result["courses"]), 8)
        self.assertEqual(result["courses"][0]["course_code"], "211501")
        self.assertEqual(result["courses"][0]["credit"], "04")
        self.assertEqual(result["courses"][0]["year"], "First Year")
        self.assertEqual(result["summary"]["total_credit"], 32.0)
        self.assertEqual(result["summary"]["yearly_gpa"]["Fourth Year"], 2.40)


if __name__ == "__main__":
    unittest.main()
