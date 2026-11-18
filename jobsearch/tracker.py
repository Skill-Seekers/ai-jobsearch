"""The application tracker: one JSON file, one entry per posting.

Guardrails: a built package is recorded as `drafted`. A status change is recorded only when the caller states
the candidate confirmed it (`--confirmed`). An empty field means NOT RECORDED, never "did not happen"."""
import difflib, glob, os, re
from datetime import date, datetime
from jobsearch.util import norm_simple, read_json, read_text, strip_jd_header, write_json

STATUSES = ('drafted', 'applied', 'screen', 'interview', 'offer', 'declined', 'closed', 'passed')
SUFFIX = re.compile(r'\b(inc|llc|ltd|plc|corp|corporation|co|company|technologies|technology|semiconductor|semiconductors|networks|network|software|systems|solutions|group|holdings|the)\b')
DEFAULT_GENERIC = {'senior', 'sr', 'staff', 'principal', 'lead', 'director', 'manager', 'engineer', 'engineering', 'technical'}


def generic_words(c):
    """Title words that never identify a requisition by themselves: seniority and level words (DEFAULT_GENERIC) plus the
    role names in config (tracker_generic_words)."""
    return DEFAULT_GENERIC | {norm_simple(w) for w in c.get('tracker_generic_words', []) if norm_simple(w)}


def load(c):
    d = read_json(c.p('tracker'), None)
    if not d:
        d = {'schema_version': '1.0', 'updated': None, 'applications': []}
    d.setdefault('applications', [])
    return d


def save(c, d):
    d['updated'] = date.today().isoformat()
    write_json(c.p('tracker'), d, indent=2)


def norm_co(s):
    s = re.sub(r'[.,()/|&–—-]', ' ', (s or '').lower())
    return re.sub(r'\s+', ' ', SUFFIX.sub(' ', s)).strip()


def match(company, title, apps, link='', generic=DEFAULT_GENERIC):
    """The tracker entry this posting is, or None. Order: a tracked posting id inside the link (exact);
    then same company plus at least two distinctive title keywords, only for entries marked applied."""
    u = str(link or '')
    for a in apps:
        sid = str(a.get('source_job_id') or '').strip()
        if sid and len(sid) >= 6 and sid in u:
            return a
    rc, rt = norm_co(company), norm_simple(title)
    if not rc:
        return None
    for a in apps:
        if not a.get('company') or not a.get('applied') or norm_co(a['company']) != rc:
            continue
        kws = [norm_simple(k) for k in (a.get('title_keywords') or []) if norm_simple(k) and norm_simple(k) not in generic]
        if not kws:
            continue
        hits = [k for k in kws if k in rt]
        hits = [k for k in hits if not any(k != o and k in o for o in hits)]     # one phrase inside another counts once
        if len(hits) >= (2 if len(kws) >= 2 else 1):
            return a
    return None


def find_dupes(c, jd_text, company='', title='', req_id='', link=''):
    """Prior applications and saved JDs that look like this posting. Run before tailoring."""
    d = load(c)
    out = {'tracker': [], 'saved_jds': []}
    jd_low = jd_text.lower()
    for a in d['applications']:
        why = []
        if req_id and (str(a.get('req_id') or '').lower() == req_id.lower() or str(a.get('source_job_id') or '') == req_id):
            why.append('same requisition id')
        if a.get('req_id') and len(str(a['req_id'])) >= 5 and str(a['req_id']).lower() in jd_low:
            why.append('requisition id %s appears in this text' % a['req_id'])
        if link and a.get('source_job_id') and str(a['source_job_id']) in link:
            why.append('same posting link')
        if company and title and match(company, title, [dict(a, applied=True)], generic=generic_words(c)):
            why.append('same company and title keywords')
        if why:
            out['tracker'].append(dict(id=a['id'], company=a.get('company'), title=a.get('title'), status=a.get('status'), outcome=a.get('outcome'), why='; '.join(sorted(set(why)))))
    base = norm_simple(strip_jd_header(jd_text))[:4000]
    if len(base) > 300:
        for p in sorted(glob.glob(os.path.join(c.p('job_descriptions'), '**', '*.*'), recursive=True)):
            if not p.lower().endswith(('.txt', '.md')):
                continue
            other = norm_simple(strip_jd_header(read_text(p) or ''))[:4000]
            if len(other) < 300:
                continue
            ratio = difflib.SequenceMatcher(None, base, other, autojunk=False).ratio()
            if ratio >= 0.85:
                out['saved_jds'].append(dict(file=os.path.relpath(p, c.root), similarity=round(ratio, 2)))
    return out


def add(c, company, title, id=None, req_id='', source_job_id='', jd_file='', folder='', title_keywords=None, tailored_date=None, note=''):
    d = load(c)
    slug = id or re.sub(r'[^a-z0-9]+', '-', ('%s %s' % (company or 'unknown', title)).lower()).strip('-')[:60]
    if any(a['id'] == slug for a in d['applications']):
        raise ValueError('tracker already has an entry with id "%s"; pick another id' % slug)
    entry = dict(id=slug, company=company or None, title=title, req_id=req_id or None, source_job_id=source_job_id or None, jd_file=jd_file or None,
                 folder=folder or None, title_keywords=title_keywords or [], status='drafted', applied=False, applied_date=None,
                 tailored_date=tailored_date or date.today().isoformat(), outcome=None, notes=note)
    d['applications'].append(entry)
    save(c, d)
    return entry


def update(c, id, status=None, applied=None, applied_date=None, outcome=None, note=None, confirmed=False):
    if not confirmed:
        raise PermissionError('Refused: a tracker status changes only when the candidate confirms it. Pass --confirmed after they say so.')
    d = load(c)
    a = next((x for x in d['applications'] if x['id'] == id), None)
    if not a:
        raise KeyError('no tracker entry with id "%s"' % id)
    if status:
        if status not in STATUSES:
            raise ValueError('status must be one of: ' + ', '.join(STATUSES))
        a['status'] = status
        if status in ('applied', 'screen', 'interview', 'offer') and applied is None:
            applied = True
    if applied is not None:
        a['applied'] = bool(applied)
    if applied_date:
        a['applied_date'] = applied_date
    if outcome:
        a['outcome'] = outcome
    if note:
        a['notes'] = (a.get('notes') + ' | ' if a.get('notes') else '') + note
    a['last_confirmed'] = date.today().isoformat()
    save(c, d)
    return a


def days_since(day, today):
    try:
        return (datetime.strptime(today, '%Y-%m-%d').date() - datetime.strptime(day, '%Y-%m-%d').date()).days
    except (TypeError, ValueError):
        return None


def rows_for_dashboard(c, today):
    out = []
    for a in load(c)['applications']:
        ref = a.get('applied_date') or a.get('tailored_date')
        out.append(dict(id=a['id'], company=a.get('company') or '(not named)', title=a.get('title') or '', req_id=a.get('req_id') or '',
                        status=a.get('status') or 'drafted', applied=bool(a.get('applied')), applied_date=a.get('applied_date') or '',
                        tailored_date=a.get('tailored_date') or '', outcome=a.get('outcome') or '', days=days_since(ref, today), notes=a.get('notes') or ''))
    return out


def report(c, today=None):
    today = today or date.today().isoformat()
    rows = rows_for_dashboard(c, today)
    cnt = {}
    for r in rows:
        cnt[r['status']] = cnt.get(r['status'], 0) + 1
    L = ['%d entries | %s' % (len(rows), ', '.join('%s %d' % kv for kv in sorted(cnt.items())) or 'none')]
    L.append('applied (candidate-confirmed): %d | drafted only: %d' % (sum(1 for r in rows if r['applied']), cnt.get('drafted', 0)))
    quiet = [r for r in rows if r['status'] == 'applied' and r['days'] is not None and r['days'] >= 14 and not r['outcome']]
    if quiet:
        L.append('applied 14+ days ago with no recorded outcome (ask the candidate; silence is not a recorded outcome):')
        L += ['  %-40s %d days' % ('%s: %s' % (r['company'], r['title'])[:40], r['days']) for r in quiet]
    return L
