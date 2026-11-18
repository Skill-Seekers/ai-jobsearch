import json, os, unittest
from helpers import WorkspaceCase, DAY
from jobsearch import seen, tracker, dashboard


class SeenTests(WorkspaceCase):
    def test_new_then_seen_and_hold(self):
        r = self.pipeline()
        f = os.path.join(r, 'scored_live.json')
        self.cli('seen', 'annotate', f)
        self.assertTrue(all(x['is_new'] for x in self.load(f)))
        self.assertEqual(self.cli('seen', 'ingest', f, '--run', '1', '--date', DAY, '--filtered', os.path.join(r, 'dropped.json'))[0], 0)
        self.cli('seen', 'annotate', f)
        self.assertFalse(any(x['is_new'] for x in self.load(f)), 'everything was seen in run 1')
        self.cli('seen', 'ingest', f, '--run', '2', '--date', '2026-10-27')
        c = self.cfg()
        s = seen.load(c)
        self.assertTrue(all(j['times_seen'] >= 2 for k, j in s['jobs'].items() if j['state'] != 'filtered' and j.get('last_score')))
        code, out, _ = self.cli('seen', 'hold', '--ids', 'li:0000000101')
        self.assertIn('held li:0000000101', out)
        code, out, _ = self.cli('seen', 'held')
        self.assertIn('NOT re-seen', out)
        self.assertIn('not found', self.cli('seen', 'hold', '--ids', 'li:9')[1])

    def test_job_keys(self):
        self.assertEqual(seen.job_key({'link': 'https://www.linkedin.com/jobs/view/senior-tpm-0000000101'}), 'li:0000000101')
        self.assertEqual(seen.job_key({'link': 'https://www.indeed.com/viewjob?jk=0000000000a1b2c3'}), 'indeed:0000000000a1b2c3')
        self.assertTrue(seen.job_key({'company': 'A', 'title': 'B', 'location': 'C'}).startswith('x:'))


class TrackerTests(WorkspaceCase):
    def test_match_rules(self):
        apps = tracker.load(self.cfg())['applications']
        self.assertEqual(tracker.match('Tailspin Cloud', 'Senior TPM, Cloud Infrastructure Capacity', apps)['id'], 'tailspin-cloud-tpm')
        self.assertIsNone(tracker.match('Tailspin Cloud', 'Technical Program Manager, Billing', apps), 'one shared generic word is not a match')
        self.assertIsNone(tracker.match('Litware Storage', 'Senior Technical Program Manager, Controller Firmware', apps), 'a drafted, unapplied entry does not match by keywords')
        self.assertEqual(tracker.match('Anyone', 'Anything', apps, 'https://www.linkedin.com/jobs/view/x-0000000204')['id'], 'litware-storage-tpm', 'tracked posting id matches regardless of company text')

    def test_status_change_needs_confirmation(self):
        c = self.cfg()
        code, out, _ = self.cli('tracker', 'update', '--id', 'litware-storage-tpm', '--status', 'applied')
        self.assertEqual(code, 1); self.assertIn('Refused', out)
        self.assertFalse(tracker.load(c)['applications'][0]['applied'])
        code, out, _ = self.cli('tracker', 'update', '--id', 'litware-storage-tpm', '--status', 'applied', '--applied-date', DAY, '--confirmed')
        self.assertEqual(code, 0)
        a = tracker.load(c)['applications'][0]
        self.assertTrue(a['applied']); self.assertEqual(a['applied_date'], DAY)
        self.assertEqual(self.cli('tracker', 'update', '--id', 'litware-storage-tpm', '--status', 'bogus', '--confirmed')[0], 2)

    def test_add_starts_as_drafted_not_applied(self):
        code, out, _ = self.cli('tracker', 'add', '--company', 'Wingtip Devices', '--title', 'Senior TPM Hardware', '--keywords', 'hardware')
        self.assertEqual(code, 0)
        e = [a for a in tracker.load(self.cfg())['applications'] if a['company'] == 'Wingtip Devices'][0]
        self.assertEqual((e['status'], e['applied']), ('drafted', False))
        self.assertEqual(self.cli('tracker', 'add', '--company', 'Wingtip Devices', '--title', 'Senior TPM Hardware')[0], 2, 'duplicate id refused')

    def test_dupe_check_finds_prior_jd(self):
        jd = self.p('resume', 'job_descriptions', 'contoso_senior-tpm-silicon-bringup.txt')
        code, out, _ = self.cli('tracker', 'dupes', '--jd', jd, '--company', 'Litware Storage', '--title', 'Controller Firmware')
        self.assertEqual(code, 1); self.assertIn('saved JD', out)


class DashboardTests(WorkspaceCase):
    def build(self, **kw):
        r = self.pipeline()
        args = ['dashboard', os.path.join(r, 'scored_live.json'), '--dropped', os.path.join(r, 'dropped.json'), os.path.join(r, 'dropped_live.json'),
                '--date', DAY, '--out', self.p('search')] + list(kw.get('extra', []))
        code, out, err = self.cli(*args)
        self.assertEqual(code, 0, out + err)
        return self.p('search', 'job_search_%s.html' % DAY)

    def test_html_has_no_leftover_placeholders_and_correct_run(self):
        html = self.slurp(self.build())
        for ph in ('__TITLE__', '__HEADING__', '__DATA__', '__NOTES_ID__'):
            self.assertNotIn(ph, html)
        data = json.loads(html.split('const DATA = ', 1)[1].split(';\nconst $ =', 1)[0].replace('<\\/', '</'))
        self.assertEqual(data['run'], 1)
        self.assertEqual(len(data['filtered']), 7)
        cutoff = '2026-10-23'
        for r in data['results']:
            self.assertEqual(r['is_new'], r['posted'] >= cutoff, 'NEW is derived from the posted date')
        order = [(r['bucket'], -r['match']) for r in data['results']]
        buckets = ['Strongest Fit', 'Strong Fit', 'Stretch / Watch']
        self.assertEqual(order, sorted(order, key=lambda t: (buckets.index(t[0]), t[1])), 'sorted by bucket, then match')

    def test_rebuild_same_day_keeps_run_number(self):
        self.build(); self.build()
        html = self.slurp(self.p('search', 'job_search_%s.html' % DAY))
        self.assertIn('"run": 1', html)

    def test_script_breakout_is_neutralised(self):
        r = self.pipeline()
        rows = self.load(r, 'scored_live.json')
        rows[0]['title'] = 'Evil </script><script>alert(1)</script>'
        rows[0]['company'] = '<img src=x onerror=alert(1)>'
        f = self.p('evil.json'); self.dump(f, rows)
        code, out, err = self.cli('dashboard', f, '--date', '2026-10-30', '--out', self.p('search_evil'))
        self.assertEqual(code, 0, err)
        html = self.slurp(self.p('search_evil', 'job_search_2026-10-30.html'))
        self.assertEqual(html.count('</script>'), 1, 'only the template closes its script tag')

    def test_csv_is_optional_and_formula_safe(self):
        r = self.pipeline()
        rows = self.load(r, 'scored_live.json')
        rows[0]['title'] = '=HYPERLINK("http://example.com","click")'
        f = self.p('csvrows.json'); self.dump(f, rows)
        self.cli('dashboard', f, '--date', '2026-10-29', '--out', self.p('search_nocsv'))
        self.assertFalse(os.path.exists(self.p('search_nocsv', 'job_search_2026-10-29.csv')), 'CSV is off unless asked for')
        self.cli('dashboard', f, '--date', '2026-10-29', '--out', self.p('search_csv'), '--csv')
        text = self.slurp(self.p('search_csv', 'job_search_2026-10-29.csv'), 'utf-8-sig')
        self.assertIn("'=HYPERLINK", text); self.assertNotIn(',=HYPERLINK', text)
        self.assertEqual(dashboard.csv_safe('+1'), "'+1")
        self.assertEqual(dashboard.csv_safe('Plain'), 'Plain')


if __name__ == '__main__':
    unittest.main()
