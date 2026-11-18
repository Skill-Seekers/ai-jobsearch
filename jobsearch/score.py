"""Keyword score (0-97), scope gate, buckets, and recorded manual adjustments.

A transparent heuristic, not a forecast. The same input always gives the same score. The base scorer saturates
near its cap, so the skill reads the top descriptions and records any change with `adjust`, each with a reason."""
import collections, os, re
from datetime import datetime, timedelta
from jobsearch.extract import parse_salary, is_remote, is_home
from jobsearch.util import load_rows, write_json, read_json

BUCKETS = ('Strongest Fit', 'Strong Fit', 'Stretch / Watch')


def score_row(r, c, fresh_from):
    S = c['scoring']
    P = S.get('points', {})
    s, why = P.get('base', 40), []
    t = c.tier_of(r['company'])
    s += S['tier_points'].get(str(t), 0)
    if t:
        why.append('tier%d' % t)
    title, desc = r['title'].lower(), (r.get('desc') or '').lower()
    blob = title * 3 + ' ' + desc
    dom = 0
    for fam, d in S['domain_families'].items():
        if any(k in blob for k in d['keywords']):
            dom += d['points']; why.append(fam)
    s += min(dom, S['domain_cap'])
    neg = 0
    for fam, kws in S['negative_families'].items():
        if any(k in title for k in kws):
            neg -= P.get('neg_title', 10); why.append('neg:' + fam)
        elif any(desc.count(k) >= 2 for k in kws):
            neg -= P.get('neg_desc', 6); why.append('neg?:' + fam)
    s += max(neg, -P.get('neg_cap', 20))
    words = S.get('level_words') or ['senior', 'sr', 'staff', 'principal', 'director', 'lead']
    if re.search(r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b', title):
        s += S['level_bonus']
    else:
        s -= S['no_level_penalty']; why.append('no-level')
    for tm in S['title_match']:
        if any(p in title for p in tm['phrases']):
            s += tm['points']; break
    else:
        s -= S['title_miss_penalty']; why.append('title-miss')
    if is_home(r, c):
        s += S['home_bonus']; why.append('home')
    elif is_remote(r):
        s += S['remote_bonus']; why.append('remote')
    else:
        s -= S['out_of_area_penalty']; why.append('out-of-area')
    if r['posted'] and r['posted'] >= fresh_from:
        s += S['fresh_bonus']
    lo, hi = parse_salary(r.get('salary', ''))
    if lo:
        if lo >= S['comp_bonus_min']:
            s += P.get('comp_bonus', 5); why.append('comp')
        elif lo < S['comp_low_penalty_below']:
            s -= P.get('comp_penalty', 6); why.append('comp-low')
    r['score'] = max(0, min(S['base_cap'], s)); r['why'] = why; r['tier'] = t
    return r


def scope_row(r, c):
    G = c['scope_gate']
    desc = r.get('desc') or ''
    m = re.search(r'(What We Need To See|Minimum Qualifications|Requirements|Qualifications)(.*)', desc, re.S | re.I)
    req = m.group(2) if m else desc
    blob = (r['title'] + ' \n ' + req).lower()
    tl = r['title'].lower()
    in_hits = len({p for p in G['in_phrases'] if re.search(p, blob, re.I)})
    scores = {}
    for dom, pats in G['out_phrases'].items():
        k = len({p for p in pats if re.search(p, blob, re.I)})
        if G.get('title_out', {}).get(dom) and re.search(G['title_out'][dom], tl):
            k += 2
        scores[dom] = k
    top = max(scores, key=scores.get) if scores else ''
    k = scores.get(top, 0)
    if k >= 2 and k > in_hits:
        r['scope'] = 'out'; r['scope_reason'] = '%s: %d distinct requirement signals vs %d in-scope' % (top, k, in_hits)
    else:
        r['scope'] = 'in'
        r['scope_reason'] = ('title suggests %s, but requirements carry %d in-scope signals' % (top, in_hits)) if k and in_hits >= k else ''
    return r


def bucket_of(r, c):
    b = c['scoring']['buckets']
    s = r['score']
    if s < b['stretch_min']:
        return 'Filtered'
    if r.get('scope') == 'out':
        return 'Stretch / Watch'
    return 'Strongest Fit' if s >= b['strongest_min'] else ('Strong Fit' if s >= b['strong_min'] else 'Stretch / Watch')


def work_mode(r):
    d, l = (r.get('desc') or '')[:600].lower(), (r.get('location') or '').lower()
    if 'remote' in l or 'fully remote' in d:
        return 'Remote'
    if 'hybrid' in d or 'hybrid' in l:
        return 'Hybrid'
    if 'on-site' in d or 'onsite' in d or 'on site' in d:
        return 'Onsite'
    return 'N/A'


def run(c, path, today, out=None):
    today_d = datetime.strptime(today, '%Y-%m-%d').date()
    fresh = (today_d - timedelta(days=c['scoring']['new_badge_days'])).isoformat()
    rows = [scope_row(score_row(r, c, fresh), c) for r in load_rows(path)]
    floor_usd = c['targets']['compensation'].get('minimum_salary')
    for r in rows:
        r['bucket'] = bucket_of(r, c)
        r['workMode'] = work_mode(r)
        note = []
        fn = c.flag_note(r['company'])
        if fn:
            note.append('⚠ ' + fn)
        lo, hi = parse_salary(r.get('salary', ''))
        if floor_usd and hi and hi < floor_usd:
            note.append('⚠ Below pay floor')
        if r.get('note'):
            note.append(r['note'])
        r['note'] = ' | '.join(note)
    rows.sort(key=lambda r: (-r['score'], r['posted'] or ''))
    out = out or os.path.join(os.path.dirname(os.path.abspath(path)), 'scored.json')
    write_json(out, rows)
    dist = collections.Counter((r['score'] // 10) * 10 for r in rows)
    top = rows[0]['score'] if rows else 0
    tied = sum(1 for r in rows if r['score'] == top)
    return dict(out=out, n=len(rows), dist=dict(sorted(dist.items(), reverse=True)), buckets=dict(collections.Counter(r['bucket'] for r in rows)),
                scope_out=sum(1 for r in rows if r['scope'] == 'out' and r['bucket'] != 'Filtered'), saturated=tied >= 5, top=top, tied=tied)


def adjust(c, path, adjustments_path, out=None):
    """Apply recorded manual adjustments. Each: {"link_contains" or "company"+"title_contains", "set" or "delta", "reason", "bucket"?}."""
    rows = load_rows(path)
    adj = read_json(adjustments_path, [])
    applied, missed = 0, []
    for a in adj:
        if a.get('link_contains'):
            hits = [r for r in rows if a['link_contains'] in r.get('link', '')]
        elif a.get('company') and a.get('title_contains'):
            hits = [r for r in rows if a['company'].lower() in r['company'].lower() and a['title_contains'].lower() in r['title'].lower()]
        else:
            raise ValueError('an adjustment needs link_contains, or company and title_contains: %r' % a)
        if not a.get('reason'):
            raise ValueError('every adjustment needs a reason: %r' % a)
        if not hits:
            missed.append(a); continue
        for r in hits:
            old = r['score']
            r['score'] = max(0, min(100, a['set'] if 'set' in a else old + a['delta']))
            r.setdefault('adjustments', []).append(dict(old=old, new=r['score'], reason=a['reason']))
            r['bucket'] = a.get('bucket') or bucket_of(r, c)
            applied += 1
    rows.sort(key=lambda r: (-r['score'], r['posted'] or ''))
    write_json(out or path, rows)
    return dict(applied=applied, missed=missed, out=out or path)
