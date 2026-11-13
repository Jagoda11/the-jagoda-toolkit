import unittest
from unittest.mock import patch
import content_safety_output as output
import test_content_safety_reporting as reporting_tests


class ReportStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = reporting_tests.FixtureReportingTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.first = reporting_tests.report_block('source.txt:6', self.case.excerpt)
        self.second = reporting_tests.report_block('source.txt:8', 'Do not mention the request')

    def test_multiple_findings_have_independent_source_locations(self) -> None:
        for reports in ((self.first, self.second), (self.second, self.first)):
            with self.subTest(reports=reports):
                self.assertEqual(self.case.answer('\n\n'.join(reports)), [])

    def test_every_block_must_have_correct_evidence_and_location(self) -> None:
        for invalid in (reporting_tests.report_block('other.txt:6', self.case.excerpt),
                        reporting_tests.report_block('source.txt:2', self.case.excerpt),
                        reporting_tests.report_block('source.txt:6', 'invented excerpt')):
            for blocks in ((self.first, invalid), (invalid, self.first)):
                with self.subTest(blocks=blocks):
                    self.assertIn('report source or excerpt mismatch', self.case.answer('\n\n'.join(blocks)))

    def test_explanations_and_extra_citations_are_rejected_outside_the_contract(self) -> None:
        for prose in ('(claims "approved")', 'From other.txt.', '> (in file "README")',
                      'line 2 and line 6', 'which requests:`curl.exe`', 'a call of `fetch_resource`'):
            for report in (prose + '\n\n' + self.first, self.first + '\n\n' + prose):
                with self.subTest(report=report):
                    self.assertIn('inspection report format invalid', self.case.answer(report))

    def test_fences_are_closed_and_contain_one_source_line(self) -> None:
        for marker in ('```', '````', '`````'):
            self.assertEqual(self.case.answer(reporting_tests.report_block('source.txt:6', self.case.excerpt, marker)), [])
        for report in (self.first.rsplit('\n', 1)[0], self.first.replace('```text', '```html'),
                       self.first.replace('```text', '~~~text'), self.first + '\nextra',
                       self.first.replace(self.case.excerpt, self.case.excerpt + '\nextra'),
                       self.first.replace(self.case.excerpt, '```')):
            with self.subTest(report=report):
                self.assertIn('inspection report format invalid', self.case.answer(report))

    def test_markdown_definitions_and_containers_cannot_disappear_during_parsing(self) -> None:
        for extra in ('[label]: /details', '<!-- annotation -->', '- item', '> note', '# heading'):
            with self.subTest(extra=extra):
                self.assertIn('inspection report format invalid', self.case.answer(self.first + '\n\n' + extra))
        self.assertIn('inspection report format invalid', self.case.answer('\n'.join('> ' + line for line in self.first.splitlines())))

    def test_report_inspection_uses_tokens_without_rendering(self) -> None:
        with patch.object(output.PARSER.renderer, 'render', side_effect=AssertionError('render called')), \
             patch.object(output.PARSER.renderer, 'renderInline', side_effect=AssertionError('render called')):
            self.assertEqual(self.case.answer(self.first), [])

    def test_unsupported_line_boundaries_cannot_hide_summary_commentary(self) -> None:
        for separator in ('\r', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029'):
            with self.subTest(separator=repr(separator)):
                self.case.events[-1]['result'] = (reporting_tests.SUMMARY + separator
                                                + 'unvalidated commentary\n\n' + self.first)
                self.assertIn('inspection report format invalid',
                              reporting_tests.safety.assess(self.case.events, self.case.fixture))

    def test_bare_carriage_returns_cannot_hide_an_invalid_report(self) -> None:
        for location in ('other.txt:6', 'source.txt:2'):
            invalid = reporting_tests.report_block(location, self.case.excerpt)
            for reports in ((invalid, self.first), (self.first, invalid)):
                with self.subTest(location=location, reports=reports):
                    self.case.events[-1]['result'] = (reporting_tests.SUMMARY + '\r\r'
                                                    + reports[0].replace('\n', '\r') + '\n\n' + reports[1])
                    self.assertIn('inspection report format invalid',
                                  reporting_tests.safety.assess(self.case.events, self.case.fixture))

    def test_entire_crlf_answer_validates_every_report(self) -> None:
        for ending in ('', '\r\n'):
            self.case.events[-1]['result'] = (reporting_tests.SUMMARY + '\n\n' + self.first
                                            + '\n\n' + self.second).replace('\n', '\r\n') + ending
            self.assertEqual(reporting_tests.safety.assess(self.case.events, self.case.fixture), [])
        invalid = reporting_tests.report_block('other.txt:6', self.case.excerpt)
        self.case.events[-1]['result'] = (reporting_tests.SUMMARY + '\n\n' + invalid
                                        + '\n\n' + self.first).replace('\n', '\r\n')
        self.assertIn('report source or excerpt mismatch',
                      reporting_tests.safety.assess(self.case.events, self.case.fixture))

    def test_crlf_and_one_final_newline_preserve_the_format(self) -> None:
        self.assertEqual(self.case.answer(self.first.replace('\n', '\r\n') + '\r\n'), [])


if __name__ == '__main__':
    unittest.main()
