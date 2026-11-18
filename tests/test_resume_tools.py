import os, unittest, zipfile, shutil
from helpers import WorkspaceCase
from jobsearch import ats, gaps


class AtsTests(WorkspaceCase):
    resume = property(lambda s: s.p('resume', 'master', 'ARivera_v1.0.docx'))
    jd = property(lambda s: s.p('resume', 'job_descriptions', 'contoso_senior-tpm-silicon-bringup.txt'))

    def test_clean_resume_reports_no_structure_warnings(self):
        text, s = ats.check(self.cfg(), self.resume, self.jd)
        self.assertEqual(s['warnings'], 0, text)
        self.assertIn('Formatting guidance only', text)
        self.assertGreater(s['coverage'], 50)

    def test_do_not_claim_terms_are_blocked_not_suggested(self):
        text, s = ats.check(self.cfg(), self.resume, self.jd)
        gaps_part = text.split('### Gaps')[1].split('### DO NOT ADD')[0]
        self.assertNotIn('pmp', gaps_part)
        self.assertIn('- pmp:', text.split('### DO NOT ADD')[1])

    def test_guard_flags_resume_that_claims_a_blocked_term(self):
        bad = self.p('bad_resume.docx')
        from build_sample_workspace import make_docx, RESUME
        make_docx(bad, RESUME + [('p', 'PMP certified')])
        text, s = ats.check(self.cfg(), bad, self.jd)
        self.assertEqual(s['claimed_violations'], 1)
        self.assertEqual(self.cli('ats', bad, self.jd)[0], 1)
        self.assertEqual(self.cli('ats', self.resume, self.jd)[0], 0)

    def test_textbox_and_missing_headings_are_warned(self):
        bad = self.p('textbox.docx')
        from build_sample_workspace import make_docx
        make_docx(bad, [('p', 'Alex Rivera'), ('p', 'Did some things.')])
        text, s = ats.check(self.cfg(), bad, self.jd)
        self.assertIn('No "Experience" heading', text)
        self.assertGreaterEqual(s['warnings'], 3)


class GapTests(WorkspaceCase):
    def test_report_marks_claimed_decided_and_gap(self):
        lines, path = gaps.report(self.cfg())
        self.assertTrue(os.path.exists(path))
        html = self.slurp(path)
        self.assertIn('Decided no', html); self.assertIn('Claimed', html)
        rows = {r['id']: r for r in self.load(os.path.dirname(path), 'skill_gap_report.json')['rows']}
        self.assertEqual(rows['npi']['status'], 'Claimed')
        self.assertEqual(rows['pmp']['status'], 'Decided no')
        self.assertEqual(rows['exec']['status'], 'Gap')

    def test_empty_vocabulary_is_a_clear_error(self):
        c = self.cfg(); c['skill_vocabulary'] = []
        with self.assertRaises(ValueError):
            gaps.report(c)

    def test_ingest_stores_terms_not_text(self):
        r = self.pipeline()
        code, out, _ = self.cli('gaps', 'ingest', os.path.join(r, 'scored_live.json'), '--run', '1')
        self.assertEqual(code, 0)
        data = self.load(self.p('search', 'state', 'skill_gap_data.json'))
        self.assertTrue(data['postings'])
        for v in data['postings'].values():
            self.assertEqual(set(v), {'run', 'score', 'terms', 'min_years'})


class DemoTests(WorkspaceCase):
    def test_demo_script_runs_end_to_end(self):
        import io, contextlib, run_demo
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ws = run_demo.main(os.path.join(self.tmp, 'demo'))
        self.assertTrue(os.path.exists(os.path.join(ws, 'search', 'job_search_2026-10-26.html')))
        self.assertTrue(os.path.exists(os.path.join(ws, 'search', 'job_search_2026-10-26.csv')))
        self.assertIn('Done. Open this file', buf.getvalue())


class CliTests(WorkspaceCase):
    def test_usage_errors_exit_2(self):
        self.assertEqual(self.cli('seen', 'ingest')[0], 2)
        self.assertEqual(self.cli('extract', '--raw', self.p('no_such_folder'), '--out', self.p('o'))[0], 2)
        os.makedirs(self.p('empty_raw'))
        self.assertEqual(self.cli('extract', '--raw', self.p('empty_raw'), '--out', self.p('o'))[0], 0, 'an empty raw folder is a valid, empty run')
        self.assertEqual(self.cli('liveness')[0], 2)

    def test_end_to_end(self):
        r = self.pipeline()
        self.assertEqual(self.cli('seen', 'ingest', os.path.join(r, 'scored_live.json'), '--run', '1', '--date', '2026-10-26')[0], 0)
        self.assertEqual(self.cli('dashboard', os.path.join(r, 'scored_live.json'), '--date', '2026-10-26', '--out', self.p('search'))[0], 0)
        self.assertEqual(self.cli('tracker', 'report')[0], 0)


if __name__ == '__main__':
    unittest.main()


class PackageTests(WorkspaceCase):
    def test_plugin_zip_has_what_skills_need_and_nothing_private(self):
        import sys, zipfile
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
        import build_plugin
        target, names = build_plugin.build(os.path.join(self.tmp, 'dist'))
        self.assertTrue(zipfile.is_zipfile(target))
        for need in ('.claude-plugin/plugin.json', 'jobsearch/cli.py', 'jobsearch/assets/dashboard_template.html', 'docs/CLI.md', 'LICENSE'):
            self.assertIn(need, names)
        self.assertFalse([n for n in names if n.startswith(('tests/', '_private', '.git')) or n.endswith('.pyc')])
        skills = {n.split('/')[1] for n in names if n.startswith('skills/')}
        self.assertEqual(skills, {'setup-workspace', 'job-search', 'tailor-application', 'resume-review', 'profile-audit', 'interview-prep', 'interview-thank-you'})
        for s in skills:                                         # every skill has frontmatter with a name that matches its folder
            body = zipfile.ZipFile(target).read('skills/%s/SKILL.md' % s).decode('utf-8')
            self.assertTrue(body.startswith('---\nname: %s\ndescription: ' % s), s)
