import copy, json, os, unittest
from helpers import WorkspaceCase
from jobsearch import config


class ConfigTests(WorkspaceCase):
    def test_sample_config_is_valid(self):
        errs, warn = config.validate(self.cfg())
        self.assertEqual(errs, [], errs)

    def mutate(self, fn):
        c = self.cfg()
        fn(c)
        return config.validate(c)[0]

    def test_rejects_paths_outside_workspace(self):
        self.assertTrue(any('inside the workspace' in e for e in self.mutate(lambda c: c['paths'].update(tracker='../elsewhere.json'))))
        self.assertTrue(any('inside the workspace' in e for e in self.mutate(lambda c: c['paths'].update(tracker='/etc/tracker.json'))))

    def test_rejects_bucket_order(self):
        self.assertTrue(any('buckets' in e for e in self.mutate(lambda c: c['scoring']['buckets'].update(strong_min=90))))

    def test_rejects_bad_regex(self):
        self.assertTrue(any('bad regex' in e for e in self.mutate(lambda c: c['scope_gate']['in_phrases'].append('(unclosed'))))

    def test_wanted_company_cannot_also_be_excluded(self):
        errs = self.mutate(lambda c: c['companies']['avoid'].append({'name': 'Contoso Semiconductor', 'aliases': [], 'reason': 'x'}))
        self.assertTrue(any('is in tier' in e for e in errs), errs)

    def test_missing_section_and_no_source(self):
        self.assertTrue(any('missing section' in e for e in self.mutate(lambda c: c.pop('liveness'))))
        def off(c):
            for v in c['sources'].values():
                if isinstance(v, dict): v['enabled'] = False
        self.assertTrue(any('no source is enabled' in e for e in self.mutate(off)))

    def test_cli_check_exit_codes(self):
        self.assertEqual(self.cli('check')[0], 0)
        bad = self.p('bad.config.json')
        c = self.load(self.cfg_path); c['paths']['tracker'] = '../x'
        self.dump(bad, c)
        from jobsearch import cli
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--config', bad, 'check']), 1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['--config', self.p('missing.json'), 'check']), 2)

    def test_exclusion_rules(self):
        c = self.cfg()
        self.assertEqual(c.excluded('Initech Holdings')[2], 'silent')
        self.assertEqual(c.excluded('Globex Corporation')[2], 'filtered')
        self.assertEqual(c.excluded('Robert Half')[0], 'staff')
        self.assertIsNone(c.excluded('Contoso Semiconductor'))
        self.assertIsNone(c.excluded('Keyhole Labs'))             # short pattern 'ey' must not match inside 'Keyhole'
        self.assertEqual(c.tier_of('Contoso Semiconductor'), 1)
        self.assertEqual(c.tier_of('Unknown Co'), 0)


if __name__ == '__main__':
    unittest.main()
