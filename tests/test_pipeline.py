import json, os, unittest
from helpers import WorkspaceCase, DAY, RUN
from jobsearch import extract, score, liveness, queries


class ExtractTests(WorkspaceCase):
    def test_extract_filters_and_dedupes(self):
        r = self.pipeline()
        keep, dropped = self.load(r, 'keep.json'), self.load(r, 'dropped.json')
        names = {(k['company'], k['title']) for k in keep}
        self.assertEqual(len([k for k in keep if k['company'] == 'Contoso Semiconductor']), 1, 'LinkedIn and Indeed copies must merge')
        self.assertEqual([k for k in keep if k['company'] == 'Contoso Semiconductor'][0]['source'], 'LinkedIn', 'LinkedIn outranks Indeed')
        self.assertEqual(len([k for k in keep if k['company'] == 'Tailspin Cloud']), 1, 'Glassdoor copy must merge')
        self.assertFalse(any(k['company'] in ('Globex Corporation', 'Initech Holdings', 'Robert Half') for k in keep))
        self.assertFalse(any('Legacy Parts' in k['title'] for k in keep), 'out of the 7-day window')
        reasons = {d['company'] + '|' + d['cat'] for d in dropped}
        self.assertIn('Globex Corporation|COMPANY', reasons)
        self.assertIn('Robert Half|COMPANY', reasons)
        self.assertIn('Fabrikam Silicon|LOCATION', reasons)
        self.assertIn('Tailspin Cloud|PAY', reasons)
        self.assertIn('Contoso Semiconductor|TITLE', reasons)
        self.assertFalse(any(d['company'] == 'Initech Holdings' for d in dropped), 'silent exclusions never appear')

    def test_title_exclusion_matches_whole_words(self):
        c = self.cfg()
        rows = [dict(companyName='Contoso Semiconductor', title=t, location='Austin, TX', postedAt=DAY, link='https://www.linkedin.com/jobs/view/x-000000%04d' % i, descriptionText='silicon')
                for i, t in enumerate(['Senior Technical Program Manager, Three-Phase Power',          # "hr" is an exclusion word, not a substring
                                       'Software Engineering Program Manager',                         # "software engineer" must not hit "engineering"
                                       'Software Engineer'], 1)]                                       # a real exclusion
        d = self.p('raw_whole_word'); os.makedirs(d, exist_ok=True)
        self.dump(os.path.join(d, 'r.json'), rows)
        res = extract.run(c, d, DAY, self.p('out_whole_word'))
        self.assertEqual(res['kept'], 2)
        self.assertEqual([r['title'] for r in self.load(self.p('out_whole_word'), 'dropped.json')], ['Software Engineer'])

    def test_indeed_link_keeps_posting_id(self):
        self.assertEqual(extract.clean_link('https://www.indeed.com/viewjob?jk=0000000000a1b2c3&from=serp&vjs=3'), 'https://www.indeed.com/viewjob?jk=0000000000a1b2c3')
        self.assertEqual(extract.clean_link('https://www.linkedin.com/jobs/view/abc-0000000101?trk=x'), 'https://www.linkedin.com/jobs/view/abc-0000000101')

    def test_salary_parsing(self):
        self.assertEqual(extract.parse_salary('$150,000 - $210,000'), (150000, 210000))
        self.assertEqual(extract.parse_salary('$150K-$210K'), (150000, 210000))
        self.assertEqual(extract.parse_salary('Not listed'), (None, None))


class ScoreTests(WorkspaceCase):
    def test_scores_are_deterministic_and_bucketed(self):
        r = self.pipeline()
        a = self.load(r, 'scored.json')
        self.cli('score', os.path.join(r, 'keep.json'), '--date', DAY, '--out', os.path.join(r, 'again.json'))
        self.assertEqual([x['score'] for x in a], [x['score'] for x in self.load(r, 'again.json')])
        c = self.cfg(); b = c['scoring']['buckets']
        for x in a:
            want = 'Filtered' if x['score'] < b['stretch_min'] else ('Stretch / Watch' if x['scope'] == 'out' else
                   'Strongest Fit' if x['score'] >= b['strongest_min'] else 'Strong Fit' if x['score'] >= b['strong_min'] else 'Stretch / Watch')
            self.assertEqual(x['bucket'], want)
            self.assertLessEqual(x['score'], c['scoring']['base_cap'])

    def test_scope_gate_caps_out_of_scope_role(self):
        r = self.pipeline()
        ml = [x for x in self.load(r, 'scored.json') if x['company'] == 'Proseware Labs'][0]
        self.assertEqual(ml['scope'], 'out')
        self.assertEqual(ml['bucket'], 'Stretch / Watch')
        silicon = [x for x in self.load(r, 'scored.json') if x['company'] == 'Contoso Semiconductor'][0]
        self.assertEqual(silicon['scope'], 'in')

    def test_adjust_requires_reason_and_reports_misses(self):
        r = self.pipeline()
        f = os.path.join(r, 'scored.json')
        adj = self.p('adj.json')
        self.dump(adj, [{'company': 'Contoso', 'title_contains': 'Bring-up', 'delta': -5, 'reason': 'test'}, {'company': 'Nobody', 'title_contains': 'x', 'delta': 1, 'reason': 'r'}])
        before = [x for x in self.load(f) if x['company'] == 'Contoso Semiconductor'][0]['score']
        code, out, err = self.cli('adjust', f, adj, '--out', os.path.join(r, 'adj_out.json'))
        self.assertEqual(code, 1, 'a missed adjustment is reported with exit code 1')
        after = [x for x in self.load(r, 'adj_out.json') if x['company'] == 'Contoso Semiconductor'][0]
        self.assertEqual(after['score'], before - 5)
        self.assertEqual(after['adjustments'][0]['reason'], 'test')
        self.dump(adj, [{'company': 'Contoso', 'title_contains': 'Bring-up', 'delta': 1}])
        self.assertEqual(self.cli('adjust', f, adj)[0], 2, 'an adjustment without a reason is refused')


class LivenessTests(WorkspaceCase):
    def test_closed_and_expired_postings_leave_the_list(self):
        r = self.pipeline()
        live, dead = self.load(r, 'scored_live.json'), self.load(r, 'dropped_live.json')
        self.assertTrue(any('Controller Firmware' in d['title'] for d in dead))
        self.assertTrue(any('Quality' in d['title'] and 'Apply-by' in d['reason'] for d in dead))
        self.assertFalse(any('Controller Firmware' in x['title'] for x in live))
        self.assertTrue(all(x['live'] == 'open' for x in live))


class QueryTests(WorkspaceCase):
    def test_batches_follow_tiers(self):
        c = self.cfg()
        self.assertEqual(queries.dedicated_companies(c)[:2], ['Contoso Semiconductor', 'Fabrikam Silicon'])
        self.assertNotIn('Adventure Works Devices', queries.dedicated_companies(c), 'tier 3 has no dedicated query')
        self.assertEqual(queries.batch_of(c, 'Northwind Networks'), 'B1')
        self.assertIsNone(queries.batch_of(c, 'Adventure Works Devices'))
        url = queries.general_urls(c)[0][1]
        self.assertIn('keywords=Technical+Program+Manager', url)

    def test_staging_progress(self):
        c = self.cfg()
        queries.mark(c, 'B1', 'DONE', DAY)
        self.assertEqual(queries.status_map(c)['B1'], 'DONE')
        self.assertNotIn('B1:', queries.render(c, 'linkedin', pending=True))


if __name__ == '__main__':
    unittest.main()
