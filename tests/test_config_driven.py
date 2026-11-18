import unittest
import helpers  # noqa: F401  (sets sys.path)
from jobsearch import ats, tracker, score


class ConfigDrivenTests(unittest.TestCase):
    def test_ats_generic_terms_come_from_config(self):
        self.assertEqual(ats.domain_patterns({'ats_generic_terms': ['zzqterm'], 'skill_vocabulary': []}), ['zzqterm'])
        self.assertEqual(ats.domain_patterns({'skill_vocabulary': []}), [])

    def test_role_names_are_not_built_into_the_tracker(self):
        self.assertNotIn('technical program manager', tracker.DEFAULT_GENERIC)
        self.assertNotIn('tpm', tracker.DEFAULT_GENERIC)
        self.assertIn('technical program manager', tracker.generic_words({'tracker_generic_words': ['Technical Program Manager']}))
        self.assertIn('senior', tracker.generic_words({}))

    def test_role_name_alone_does_not_match_a_requisition(self):
        apps = [{'id': 'x', 'company': 'Tailspin Cloud', 'applied': True, 'title_keywords': ['technical program manager', 'billing']}]
        cfg = {'tracker_generic_words': ['technical program manager']}
        self.assertIsNone(tracker.match('Tailspin Cloud', 'Technical Program Manager, Storage', apps, generic=tracker.generic_words(cfg)))

    def test_score_points_default_to_previous_values(self):
        with open(score.__file__, encoding='utf-8') as fh:
            src = fh.read()
        for needle in ("P.get('base', 40)", "P.get('neg_title', 10)", "P.get('neg_cap', 20)", "P.get('comp_bonus', 5)", "P.get('comp_penalty', 6)"):
            self.assertIn(needle, src)


if __name__ == '__main__':
    unittest.main()
