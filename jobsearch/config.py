"""Load and validate jobsearch.config.json, and answer questions about it (tiers, exclusions, paths)."""
import os, re, sys
from jobsearch.util import hit, norm, read_json

CONFIG_NAME = 'jobsearch.config.json'
PATH_KEYS = ('master_resume', 'metrics_worksheet', 'job_descriptions', 'tailored', 'tracker', 'search', 'interview', 'profile')


class ConfigError(Exception):
    pass


class Config(dict):
    """A dict with a .root (the workspace folder) and helper methods."""
    root = '.'
    path = ''

    def p(self, key, *more):
        """Absolute path for a key in `paths` (or a relative path), inside the workspace."""
        rel = self['paths'].get(key, key)
        return os.path.normpath(os.path.join(self.root, rel, *more))

    def state_dir(self):
        d = os.path.join(self.p('search'), 'state')
        os.makedirs(d, exist_ok=True)
        return d

    # ---- companies
    def tiers(self):
        """[(tier:int, name, [aliases])] in config order."""
        out = []
        for t, items in sorted(self['companies']['tiers'].items()):
            for c in items:
                out.append((int(t), c['name'], c.get('aliases', [])))
        return out

    def tier_of(self, company):
        n = norm(company)
        best = 0
        for t, name, aliases in self.tiers():
            if any(hit(norm(k), n) for k in [name] + aliases) and (best == 0 or t < best):
                best = t
        return best

    def excluded(self, company):
        """(reasonType, reason, visibility) if this company must not be listed, else None."""
        n = norm(company)
        if not n:
            return None
        co = self['companies']
        for a in co.get('avoid', []):
            if any(hit(norm(k), n) for k in [a['name']] + a.get('aliases', [])):
                return ('excl', 'Excluded company: %s' % (a.get('reason') or a['name']), a.get('visibility', 'filtered'))
        if any(hit(k, n) for k in co.get('staffing_patterns', [])):
            return ('staff', 'Staffing agency / third-party recruiter posting.', 'filtered')
        if any(hit(k, n) for k in co.get('consulting_patterns', [])):
            return ('staff', 'Consulting firm posting, not a direct employer role.', 'filtered')
        if co.get('exclude_defense') and any(hit(k, n) for k in co.get('defense_patterns', [])):
            return ('wrong', 'Defense prime / clearance-gated, outside target industries.', 'filtered')
        return None

    def flag_note(self, company):
        n = norm(company)
        for f in self['companies'].get('flag_only', []):
            if any(hit(norm(k), n) for k in [f['name']] + f.get('aliases', [])):
                return f.get('note') or 'Flagged company'
        return ''


def find_config(start=None):
    """Explicit path, then $JOBSEARCH_CONFIG, then the nearest jobsearch.config.json at or above the cwd."""
    if start:
        return start
    env = os.environ.get('JOBSEARCH_CONFIG')
    if env:
        return env
    d = os.getcwd()
    while True:
        cand = os.path.join(d, CONFIG_NAME)
        if os.path.exists(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            raise ConfigError('No %s found at or above %s. Run the setup-workspace skill, or pass --config.' % (CONFIG_NAME, os.getcwd()))
        d = parent


def load(path=None):
    path = os.path.abspath(find_config(path))
    if not os.path.exists(path):
        raise ConfigError('Config not found: ' + path)
    try:
        data = read_json(path)
    except ValueError as e:
        raise ConfigError('Config is not valid JSON: %s' % e)
    cfg = Config(data)
    cfg.root = os.path.dirname(path)
    cfg.path = path
    return cfg


def _regexes(errs, label, patterns):
    for p in patterns:
        try:
            re.compile(p)
        except re.error as e:
            errs.append('%s: bad regex %r (%s)' % (label, p, e))


def validate(c):
    """(errors, warnings) for a loaded config."""
    errs, warn = [], []
    for k in ('schema_version', 'candidate', 'paths', 'targets', 'companies', 'sources', 'scoring', 'scope_gate', 'liveness', 'outputs'):
        if k not in c:
            errs.append('missing section: ' + k)
    if errs:
        return errs, warn
    for k in PATH_KEYS:
        v = c['paths'].get(k)
        if not v:
            errs.append('paths.%s is missing' % k)
        elif os.path.isabs(v) or '..' in v.replace('\\', '/').split('/'):
            errs.append('paths.%s must stay inside the workspace (no absolute paths, no ..): %s' % (k, v))
    if not c['candidate'].get('name'):
        errs.append('candidate.name is empty')
    if not c['targets'].get('roles_primary'):
        errs.append('targets.roles_primary is empty')
    sc = c['scoring']
    b = sc.get('buckets', {})
    try:
        if not (b['strongest_min'] > b['strong_min'] > b['stretch_min'] >= sc['hard_floor']):
            errs.append('scoring.buckets must be strictly decreasing and at or above hard_floor')
    except KeyError as e:
        errs.append('scoring is missing ' + str(e))
    for fam, d in sc.get('domain_families', {}).items():
        if not d.get('keywords') or not isinstance(d.get('points'), (int, float)):
            errs.append('scoring.domain_families.%s needs keywords and numeric points' % fam)
    for k in ('tier_points',):
        if k not in sc:
            errs.append('scoring.%s is missing' % k)
    sg = c['scope_gate']
    _regexes(errs, 'scope_gate.in_phrases', sg.get('in_phrases', []))
    for dom, pats in sg.get('out_phrases', {}).items():
        _regexes(errs, 'scope_gate.out_phrases.' + dom, pats)
        if dom not in sg.get('title_out', {}):
            errs.append('scope_gate.title_out is missing domain "%s"' % dom)
    _regexes(errs, 'scope_gate.title_out', sg.get('title_out', {}).values())
    _regexes(errs, 'liveness', c['liveness'].get('closed_text_patterns', []) + c['liveness'].get('deadline_patterns', []))
    for v in c.get('skill_vocabulary', []):
        _regexes(errs, 'skill_vocabulary.' + v.get('id', '?'), v.get('patterns', []))
    # a wanted company must not also be excluded
    names = [n for _, n, _ in c.tiers()]
    if len(names) != len(set(x.lower() for x in names)):
        errs.append('a company appears more than once in companies.tiers')
    for t, name, aliases in c.tiers():
        r = c.excluded(name)
        if r:
            errs.append('"%s" is in tier %d but is excluded: %s' % (name, t, r[1]))
    for a in c['companies'].get('avoid', []):
        if a.get('visibility', 'filtered') not in ('silent', 'filtered'):
            errs.append('companies.avoid "%s": visibility must be "silent" or "filtered"' % a['name'])
    if not c['outputs'].get('dashboard', True):
        warn.append('outputs.dashboard is false: the dashboard is always produced; this setting is ignored')
    enabled = [k for k, v in c['sources'].items() if isinstance(v, dict) and v.get('enabled')]
    if not enabled:
        errs.append('no source is enabled under sources')
    if not c['companies'].get('tiers', {}).get('1') and not c['companies'].get('tiers', {}).get('2'):
        warn.append('no tier 1 or tier 2 companies: no company-specific LinkedIn queries will be generated')
    for key in ('master_resume', 'metrics_worksheet'):
        if not os.path.exists(c.p(key)):
            warn.append('paths.%s does not exist yet: %s' % (key, c['paths'][key]))
    return errs, warn


def show(c):
    t = c['targets']
    lines = ['Config: %s' % c.path,
             'Candidate: %s | roles: %s' % (c['candidate']['name'], '; '.join(t['roles_primary'][:3])),
             'Companies: %s' % ', '.join('tier %s: %d' % (k, len(v)) for k, v in sorted(c['companies']['tiers'].items())),
             'Avoid: %d | staffing patterns: %d | title exclusions: %d' % (len(c['companies'].get('avoid', [])), len(c['companies'].get('staffing_patterns', [])), len(c.get('title_exclusions', []))),
             'Sources enabled: %s' % ', '.join(k for k, v in c['sources'].items() if isinstance(v, dict) and v.get('enabled')),
             'Buckets: Strongest >= %d | Strong >= %d | Stretch >= %d | window %d days' % (
                 c['scoring']['buckets']['strongest_min'], c['scoring']['buckets']['strong_min'], c['scoring']['buckets']['stretch_min'], c['scoring']['posted_within_days']),
             'Outputs: dashboard%s' % (' + CSV' if c['outputs'].get('csv') else '')]
    return '\n'.join(lines)
