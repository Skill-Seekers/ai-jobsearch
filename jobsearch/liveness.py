"""Is this posting still open? Job-site pages often cannot be fetched, so the evidence is:
  1. the posting appeared in THIS run's own search results            -> open as of the run date
  2. the posting text says closed / filled / expired                   -> closed
  3. the posting text names an apply-by date that has passed           -> expired
  4. a held role from an earlier run that did not reappear             -> unconfirmed; re-run its batch"""
import os, re
from datetime import date, datetime
from jobsearch import queries, seen
from jobsearch.util import load_rows, write_json

MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def parse_md(txt, year):
    m = re.match(r'([A-Za-z]{3,9})\.? (\d{1,2})(?:, ?(\d{4}))?', txt.strip())
    if not m or m.group(1)[:3].lower() not in MONTHS:
        return None
    try:
        return date(int(m.group(3) or year), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
    except ValueError:
        return None


def assess(row, today, c):
    desc = row.get('desc') or ''
    low = desc.lower()
    for p in c['liveness']['closed_text_patterns']:
        m = re.search(p, low)
        if m:
            return 'closed-text', 'Posting says it is closed: "%s"' % m.group(0)
    for p in c['liveness']['deadline_patterns']:
        for m in re.finditer(p, desc, re.I):
            d = parse_md(m.group(1), today.year)
            if d and d < today:
                return 'deadline-passed', 'Apply-by date %s has passed' % d.isoformat()
    return 'open', 'Appeared in the %s search' % today.isoformat()


def check(c, path, day, out_dir=None):
    today = datetime.strptime(day, '%Y-%m-%d').date()
    keep, dropped = [], []
    for r in load_rows(path):
        state, why = assess(r, today, c)
        r['live'], r['live_note'], r['live_checked'] = state, why, day
        if state == 'open':
            keep.append(r)
        else:
            d = dict(r); d.update(reasonType='wrong', reason='Posting no longer open: ' + why, cat='CLOSED')
            dropped.append(d)
    out_dir = out_dir or os.path.dirname(os.path.abspath(path))
    write_json(os.path.join(out_dir, 'scored_live.json'), keep)
    write_json(os.path.join(out_dir, 'dropped_live.json'), dropped)
    return keep, dropped


def held_report(c):
    """Lines describing held roles and which batches to re-run."""
    s = seen.load(c)
    held = [(k, j) for k, j in s['jobs'].items() if j.get('state') == 'held']
    if not held:
        return ['no held roles'], {}, []
    rerun, manual, lines = {}, [], ['Held roles (%d):' % len(held)]
    for k, j in held:
        reseen = j['last_seen'] > j.get('held_since', j['first_seen'])
        b = queries.batch_of(c, j['company'])
        lines.append('  %-14s %-24s %-44s %s' % (k, j['company'][:24], j['title'][:44],
                     ('RE-SEEN %s -> open' % j['last_seen']) if reseen else ('NOT re-seen; re-run %s' % b if b else 'NOT re-seen; no dedicated batch')))
        if j['times_seen'] > 1:
            lines.append('                 (first seen %s, runs %s: an older req, not a new posting)' % (j['first_seen'], j['runs']))
        if not reseen:
            (rerun.setdefault(b, []).append(j['company']) if b else manual.append(j))
    if rerun:
        lines.append('\nRe-run these batches so the search itself shows the roles are still open:')
        lines += ['  %s  (%s)' % (b, ', '.join(sorted(set(cs)))) for b, cs in sorted(rerun.items())]
    if manual:
        lines.append('\nNo dedicated batch (general queries only). Check the company careers page, or accept "unconfirmed":')
        lines += ['  %s | %s | %s' % (j['company'], j['title'], j.get('link', '')) for j in manual]
    return lines, rerun, manual
