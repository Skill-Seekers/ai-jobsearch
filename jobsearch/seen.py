"""Cross-run memory of every posting a search has seen (new vs seen before, reposts, held roles).

Store: <search>/state/seen_jobs.json, keyed by the board's own posting id (li:<id>, indeed:<jk>) or a hash."""
import collections, hashlib, os, re
from datetime import date
from jobsearch.util import load_rows, norm_simple, read_json, write_json
from jobsearch import tracker


def store_path(c):
    return os.path.join(c.state_dir(), 'seen_jobs.json')


def load(c):
    return read_json(store_path(c), {'schema_version': '1.0', 'updated': None, 'jobs': {}, 'runs': {}})


def save(c, s):
    s['updated'] = date.today().isoformat()
    write_json(store_path(c), s)


def job_key(row):
    link = str(row.get('link') or row.get('url') or '')
    m = re.search(r'/jobs/view/(?:[^?/]*?-)?(\d{8,12})(?:[/?]|$)', link) or re.search(r'-(\d{8,12})(?:\?|$)', link)
    if m:
        return 'li:' + m.group(1)
    m = re.search(r'[?&]jk=([0-9a-f]{8,})', link)
    if m:
        return 'indeed:' + m.group(1)
    h = hashlib.md5(('%s|%s|%s' % (norm_simple(row.get('company')), ' '.join(norm_simple(row.get('title')).split()[:8]),
                                    norm_simple((row.get('location') or '').split(',')[0]))).encode()).hexdigest()[:10]
    return 'x:' + h


def title_key(row):
    return '%s|%s|%s' % (norm_simple(row.get('company')), ' '.join(norm_simple(row.get('title')).split()[:8]), norm_simple((row.get('location') or '').split(',')[0]))


def pick(row):
    return dict(company=(row.get('company') or '').strip(), title=re.sub(r'\s+', ' ', (row.get('title') or '').replace('\U0001F195', '')).strip(),
                location=(row.get('location') or '').strip(), posted=(row.get('posted') or '')[:10], link=(row.get('link') or '').split('?')[0],
                source=row.get('source') or '')


def _index(s):
    idx = {}
    for k, j in s['jobs'].items():
        idx.setdefault(title_key(j), []).append(k)
    return idx


def add_row(s, row, run, day, state, idx, stats, batch_counts, reason=None):
    base = pick(row)
    if not base['company'] or not base['title']:
        return
    k = job_key(row)
    j = s['jobs'].get(k)
    if j is None:
        j = dict(base, first_seen=day, first_run=run, last_seen=day, last_run=run, runs=[run], times_seen=0)
        prior = [x for x in idx.get(title_key(base), []) if x != k and s['jobs'][x]['last_run'] < run]
        if prior and batch_counts.get(title_key(base), 1) == 1:      # several identical titles in ONE search are parallel openings
            j['repost_of'] = prior[0]; stats['repost'] += 1
        stats['new'] += 1
        s['jobs'][k] = j
        idx.setdefault(title_key(base), []).append(k)
    else:
        stats['seen'] += 1
        if run not in j['runs']:
            j['runs'].append(run)
        if day >= j['last_seen']:
            j['last_seen'], j['last_run'] = day, max(run, j.get('last_run', run))
        for f in ('posted', 'link', 'location'):
            if base[f] and not j.get(f):
                j[f] = base[f]
    j['times_seen'] = len(j['runs'])
    if row.get('score') is not None:
        j['best_score'] = max(row['score'], j.get('best_score', 0)); j['last_score'] = row['score']
    rank = {'seen': 0, 'filtered': 1, 'listed': 2}
    if j.get('state') not in ('held', 'applied') and rank.get(state, 0) >= rank.get(j.get('state'), -1):
        j['state'] = state
    if state == 'filtered':
        j['filter_reason'] = reason


def link_tracker(c, s):
    apps = tracker.load(c)['applications']
    ids = {'li:' + str(a['source_job_id']): a['id'] for a in apps if a.get('source_job_id')}
    for k, j in s['jobs'].items():
        t = ids.get(k) or (tracker.match(j['company'], j['title'], apps, j.get('link', ''), generic=tracker.generic_words(c)) or {}).get('id')
        if t:
            j['tracker_id'] = t
        else:
            j.pop('tracker_id', None)


def ingest(c, path, run, day, filtered=None, state='listed'):
    s = load(c); idx = _index(s)
    stats = dict(new=0, seen=0, repost=0)
    rows = load_rows(path)
    filt = load_rows(filtered) if filtered else []
    bc = collections.Counter(title_key(r) for r in rows + filt)
    for r in rows:
        add_row(s, r, run, day, state, idx, stats, bc)
    for r in filt:
        add_row(s, r, run, day, 'filtered', idx, stats, bc, reason=r.get('reason'))
    s['runs'].setdefault(str(run), {}).update(date=day, rows_ingested=len(rows))
    link_tracker(c, s)
    save(c, s)
    stats.update(rows=len(rows), total=len(s['jobs']))
    return stats


def annotate(c, path):
    """Add first_seen, times_seen, is_new, repost_of to each row of FILE (in place). Call before ingest."""
    s = load(c)
    rows = load_rows(path)
    for r in rows:
        j = s['jobs'].get(job_key(r))
        if j:
            r.update(first_seen=j['first_seen'], times_seen=j['times_seen'], is_new=j['times_seen'] <= 0)
            if j.get('repost_of'):
                r['repost_of'] = j['repost_of']
        else:
            r.update(is_new=True, times_seen=0)
    write_json(path, rows)
    return sum(1 for r in rows if r['is_new']), len(rows)


def report(c, run=None, final=False):
    s = load(c)
    jobs = s['jobs']
    if not s['runs']:
        return ['No runs recorded yet.']
    run = int(run) if run else max(int(r) for r in s['runs'])
    cur = {k: j for k, j in jobs.items() if run in j['runs']}
    new = [j for j in cur.values() if j['first_run'] == run]
    L = ['=== Run %d: %d postings seen, %d NEW, %d seen before ===' % (run, len(cur), len(new), len(cur) - len(new))]
    top = sorted([j for j in new if j.get('last_score')], key=lambda j: -j['last_score'])[:15]
    if top:
        L.append('\nNEW and scored (top 15):')
        L += ['  %3d %-24s %-52s %s' % (j['last_score'], j['company'][:24], j['title'][:52], j['location'][:22]) for j in top]
    rp = [(k, j) for k, j in cur.items() if j.get('repost_of') and j.get('state') != 'filtered']
    if rp:
        L.append('\nREPOSTS (same company, title and city as an earlier posting under a different id):')
        for k, j in rp:
            old = jobs.get(j['repost_of'], {})
            L.append('  %-24s %-48s earlier first seen %s -> new id %s%s' % (j['company'][:24], j['title'][:48], old.get('first_seen', '?'), k,
                     '  [TRACKED: %s]' % old['tracker_id'] if old.get('tracker_id') else ''))
    held = [(k, j) for k, j in jobs.items() if j.get('state') == 'held']
    if held:
        L.append('\nHELD for re-check (%d):' % len(held))
        for k, j in held:
            L.append('  %-14s %-24s %-46s last seen %s %s' % (k, j['company'][:24], j['title'][:46], j['last_seen'],
                     'RE-SEEN (still open)' if j['last_seen'] > j.get('held_since', j['first_seen']) else 'not re-seen yet'))
    if final:
        gone = [j for k, j in jobs.items() if j.get('state') == 'listed' and j.get('last_score', 0) >= 65 and j['last_run'] == run - 1 and run not in j['runs']]
        if gone:
            L.append('\nSCORED 65+ LAST RUN, NOT IN THIS RUN (closed, aged out of the window, or filtered):')
            L += ['  %3d %-24s %-50s posted %s' % (j['last_score'], j['company'][:24], j['title'][:50], j['posted']) for j in sorted(gone, key=lambda j: -j['last_score'])[:20]]
    stale = [j for j in cur.values() if j['times_seen'] >= 3 and j.get('state') == 'listed' and not j.get('tracker_id') and j.get('last_score', 0) >= 80]
    if stale:
        L.append('\nSTRONG roles seen in 3+ runs with NO application (long-open reqs, still unclaimed):')
        L += ['  %3d %-24s %-50s first seen %s (%d runs)' % (j['last_score'], j['company'][:24], j['title'][:50], j['first_seen'], j['times_seen']) for j in sorted(stale, key=lambda j: -j['last_score'])[:15]]
    return L


def hold(c, ids, hold=True, day=None):
    s = load(c); msgs = []
    for i in ids:
        k = i if ':' in i else 'li:' + i
        if k not in s['jobs']:
            msgs.append('not found: ' + k); continue
        if hold:
            s['jobs'][k]['state'] = 'held'; s['jobs'][k]['held_since'] = day or date.today().isoformat()
        elif s['jobs'][k].get('state') == 'held':
            s['jobs'][k]['state'] = 'seen'
        msgs.append(('held ' if hold else 'released ') + k)
    save(c, s)
    return msgs


def stats(c):
    s = load(c)
    cnt = collections.Counter(j.get('state') for j in s['jobs'].values())
    return 'postings %d | runs %d | %s | reposts %d | tracked %d | seen in 2+ runs %d' % (
        len(s['jobs']), len(s['runs']), dict(cnt), sum(1 for j in s['jobs'].values() if j.get('repost_of')),
        sum(1 for j in s['jobs'].values() if j.get('tracker_id')), sum(1 for j in s['jobs'].values() if j['times_seen'] > 1))
