import unittest
import test_content_safety_reporting as reporting_tests


class SourceTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = reporting_tests.FixtureReportingTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_literal_filename_characters_are_preserved(self) -> None:
        for name in ('README', 'source.txt..', r'folder\source.txt', 'source name.txt', 'source:part.txt'):
            self.case.fixture = self.case.fixture.rename(self.case.fixture.with_name(name))
            self.case.refresh_events()
            for source in (name, str(self.case.fixture)):
                with self.subTest(source=source):
                    report = reporting_tests.report_block(f'{source}:6', self.case.excerpt)
                    self.assertEqual(self.case.answer(report), [])

    def test_quoted_or_spaced_wrong_sources_cannot_become_anonymous_lines(self) -> None:
        for left, right in (('"', '"'), ("'", "'"), ('“', '”'), ('‘', '’'), ('`', '`')):
            for spacing in ('', ' ', '\t'):
                for suffix in ('6', ' line 6', 'line 6'):
                    with self.subTest(left=left, spacing=spacing, suffix=suffix):
                        location = f'{left}README{right}{spacing}:{suffix}'
                        self.assertIn('report source or excerpt mismatch', self.case.answer(
                            reporting_tests.report_block(location, self.case.excerpt)))

    def test_full_path_must_match_without_alias_resolution(self) -> None:
        for source in ('./source.txt', 'other/source.txt', str(self.case.fixture.parent / 'other.txt'), 'SOURCE.TXT'):
            with self.subTest(source=source):
                self.assertIn('report source or excerpt mismatch', self.case.answer(
                    reporting_tests.report_block(f'{source}:6', self.case.excerpt)))

    def test_trailing_periods_are_filename_data(self) -> None:
        self.case.fixture = self.case.fixture.rename(self.case.fixture.with_name('source.txt..'))
        self.case.refresh_events()
        self.assertEqual(self.case.answer(reporting_tests.report_block('source.txt..:6', self.case.excerpt)), [])
        for location in ('source.txt:6', 'source.txt.:6', '"source.txt..":6'):
            with self.subTest(location=location):
                self.assertIn('report source or excerpt mismatch', self.case.answer(
                    reporting_tests.report_block(location, self.case.excerpt)))


    def test_source_header_label_is_exact(self) -> None:
        canonical = reporting_tests.report_block('source.txt:6', self.case.excerpt)
        for label in ('source:', 'File:', 'Source :', ''):
            with self.subTest(label=label):
                self.assertIn('report source or excerpt mismatch',
                              self.case.answer(canonical.replace('Source:', label, 1)))



if __name__ == '__main__':
    unittest.main()
