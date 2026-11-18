"""Mechanical lint of the skills: the commands they tell Claude to run must parse against the real CLI, every file
they point at must exist, and every skill must carry its guardrails. This does not prove a skill behaves well in a live
session (nothing here can); it catches the drift that breaks one: a renamed flag, a moved file, a deleted gate."""
import os, re, shlex, unittest, io, contextlib
from helpers import ROOT
from jobsearch import cli

SKILLS = os.path.join(ROOT, 'skills')
COMMANDS = set(cli.HANDLERS)
EXPECTED = {'setup-workspace', 'job-search', 'tailor-application', 'resume-review', 'profile-audit', 'interview-prep', 'interview-thank-you'}
ROLE_FILES = {'job-search': 'role-profile.md', 'tailor-application': 'role-vocabulary.md', 'resume-review': 'role-checklist.md',
              'interview-prep': 'role-question-bank.md', 'profile-audit': 'role-keywords.md'}


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def skill_texts():
    for name in sorted(os.listdir(SKILLS)):
        d = os.path.join(SKILLS, name)
        for dp, _, fns in os.walk(d):
            for fn in fns:
                if fn.endswith('.md'):
                    yield name, os.path.join(dp, fn)


def command_spans(text):
    """Backtick spans (and fenced lines) that start with a jobsearch command word, or 'python3 <plugin root>/jobsearch ...'."""
    spans = re.findall(r'`([^`\n]+)`', text)
    for block in re.findall(r'```[a-z]*\n(.*?)```', text, re.S):
        spans += [l for l in block.split('\n') if l.strip()]
    for s in spans:
        s = s.strip()
        s = re.sub(r'^python3? <plugin root>/jobsearch\s+', '', s)
        w = s.split(' ', 1)[0]
        if w in COMMANDS and len(s.split()) >= 1 and not s.startswith(('check\u00a0',)):
            yield s


def normalise(s):
    s = re.sub(r'<[^<>]*>', 'x', s)
    s = s.replace('$R', 'r').replace('...', '').replace('[', '').replace(']', '').replace('|', ' ')
    s = re.sub(r'\bx x\b', 'x', s)
    return s


class SkillLint(unittest.TestCase):
    def test_exactly_the_seven_skills_with_frontmatter(self):
        self.assertEqual({d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))}, EXPECTED)
        for n in EXPECTED:
            t = read(os.path.join(SKILLS, n, 'SKILL.md'))
            m = re.match(r'---\nname: (.+)\ndescription: (.+)\n---\n', t)
            self.assertTrue(m, n)
            self.assertEqual(m.group(1), n)
            self.assertLessEqual(len(m.group(2)), 1024, n)
            self.assertNotIn('<', m.group(2), n)

    def test_commands_in_skills_parse_against_the_cli(self):
        parser = cli.build_parser()
        checked = 0
        for name, path in skill_texts():
            for span in command_spans(read(path)):
                argv = shlex.split(normalise(span).replace('"', ' ').replace("'", ' '))
                # alternatives such as "tracker add|update" were split on '|'; only test the first word's validity
                if argv[0] == 'tracker' and len(argv) > 1 and argv[1] not in ('match', 'dupes', 'add', 'update', 'report'):
                    continue
                err = io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    try:
                        parser.parse_args(argv)
                    except SystemExit as e:
                        # missing required positionals/options are fine in prose ("score keep.json" has them; "queries --pending" too);
                        # unknown flags and bad choices are not
                        msg = err.getvalue()
                        if 'unrecognized arguments' in msg or 'invalid choice' in msg or 'ambiguous option' in msg:
                            self.fail('%s: "%s" -> %s' % (os.path.relpath(path, ROOT), span, msg.strip().splitlines()[-1]))
                checked += 1
        self.assertGreater(checked, 25, 'the lint found too few commands to be meaningful')

    def test_every_referenced_file_exists(self):
        for name, path in skill_texts():
            text = read(path)
            for ref in re.findall(r'`((?:references|assets)/[A-Za-z0-9_./-]+)`', text):
                self.assertTrue(os.path.exists(os.path.join(SKILLS, name, ref)), '%s mentions %s' % (os.path.relpath(path, ROOT), ref))
            for ref in re.findall(r'`(docs/[A-Za-z0-9_./-]+\.md)`', text):
                self.assertTrue(os.path.exists(os.path.join(ROOT, ref)), '%s mentions %s' % (os.path.relpath(path, ROOT), ref))
            for ref in re.findall(r'`(skills/[A-Za-z0-9_./-]+)`', text):
                self.assertTrue(os.path.exists(os.path.join(ROOT, ref)), '%s mentions %s' % (os.path.relpath(path, ROOT), ref))

    def test_role_files_say_they_are_examples_and_point_to_adapting(self):
        for skill, fn in ROLE_FILES.items():
            t = read(os.path.join(SKILLS, skill, 'references', fn))
            self.assertIn('EXAMPLE', t.split('\n')[0], fn)
            self.assertIn('worked example', t.lower(), fn)
            self.assertIn('ADAPTING', t, fn)
            self.assertIn('references/' + fn, read(os.path.join(SKILLS, skill, 'SKILL.md')), '%s does not point to its role file' % skill)

    def test_guardrails_are_present(self):
        must = {'tailor-application': ['No fabrication', 'Type go', 'drafted', '--confirmed', 'Never overwrite'],
                'resume-review': ['never overwritten', 'verbatim', 'formatting guidance only'],
                'job-search': ['Only listings returned by a real source', '--confirmed', 'Mock or sample data is never used'],
                'interview-prep': ['Never invent', '[needs number]'],
                'profile-audit': ['Never invent'],
                'setup-workspace': ['Never invent a value', 'do_not_claim'],
                'interview-thank-you': ['Do not ask extra follow-ups']}
        for skill, phrases in must.items():
            t = read(os.path.join(SKILLS, skill, 'SKILL.md'))
            for p in phrases:
                self.assertIn(p, t, '%s lost its guardrail text: %s' % (skill, p))

    def test_config_keys_named_in_skills_exist_in_the_sample(self):
        import json
        cfg = json.loads(read(os.path.join(ROOT, 'examples', 'sample-workspace', 'jobsearch.config.json')))
        flat = set()
        def walk(d, pre=''):
            for k, v in d.items():
                flat.add(k); flat.add(pre + k)
                if isinstance(v, dict) and not k.startswith('_'):
                    walk(v, k + '.')
        walk(cfg)
        for name, path in skill_texts():
            for key in re.findall(r'`((?:scoring|targets|companies|sources|scope_gate|outputs|staging|paths|liveness)\.[a-z_]+)`', read(path)):
                self.assertIn(key, flat, '%s names config key %s that the sample config does not have' % (os.path.relpath(path, ROOT), key))
            for key in re.findall(r'`(do_not_claim|claims_limits|skill_vocabulary|title_exclusions|hard_rules)`', read(path)):
                self.assertIn(key, cfg, key)


class PersonalDataLint(unittest.TestCase):
    """Cheap in-repo checks that run without the private denylist (the real gate is tools/privacy_scan.py)."""
    def test_no_personal_paths_or_real_contacts(self):
        bad = re.compile(r'C:\\\\Users|/Users/[a-z]|/home/[a-z]|@gmail\.com|linkedin\.com/in/|\bsk-[A-Za-z0-9]{20,}')
        for dp, dns, fns in os.walk(ROOT):
            dns[:] = [d for d in dns if d not in ('.git', '__pycache__', 'tools')]
            for fn in fns:
                if fn.endswith(('.md', '.py', '.json', '.html', '.txt')) and 'test_skills' not in fn:
                    t = read(os.path.join(dp, fn))
                    m = bad.search(t)
                    self.assertIsNone(m, '%s contains %r' % (os.path.relpath(os.path.join(dp, fn), ROOT), m and m.group(0)))


if __name__ == '__main__':
    unittest.main()


class DocLinks(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        for dp, dns, fns in os.walk(ROOT):
            dns[:] = [d for d in dns if d not in ('.git', '__pycache__', 'dist')]
            for fn in fns:
                if not fn.endswith('.md'):
                    continue
                path = os.path.join(dp, fn)
                for target in re.findall(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', read(path)):
                    if re.match(r'[a-z]+:', target):
                        continue
                    self.assertTrue(os.path.exists(os.path.normpath(os.path.join(dp, target))), '%s links to missing %s' % (os.path.relpath(path, ROOT), target))


class VersionConsistency(unittest.TestCase):
    def test_package_and_plugin_versions_match(self):
        import json
        from jobsearch import __version__
        meta = json.loads(read(os.path.join(ROOT, '.claude-plugin', 'plugin.json')))
        market = json.loads(read(os.path.join(ROOT, '.claude-plugin', 'marketplace.json')))
        self.assertEqual(meta['version'], __version__)
        self.assertEqual(meta['name'], 'ai-jobsearch')
        self.assertEqual(market['plugins'][0]['name'], meta['name'])
        self.assertIn('0.2.0', read(os.path.join(ROOT, 'CHANGELOG.md')).split('\n')[2])
