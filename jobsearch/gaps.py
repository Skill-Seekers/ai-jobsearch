"""Skill-gap view: what do the roles you target ask for, and where do you stand?

Corpus A: every saved job description under paths.job_descriptions.
Corpus B: term sets from strong-fit postings of each scrape (only matched terms are stored, never the posting text).
Status comes from the candidate's own files, never guessed:
  Claimed     the term appears in the master resume
  Decided no  on the do_not_claim list
  Gap         asked for, not on the resume, no decision recorded
The vocabulary is config.skill_vocabulary, so a different role replaces it."""
import collections, glob, hashlib, html as H, os, re, statistics
from datetime import date
from jobsearch import seen, tracker
from jobsearch.util import read_json, write_json, read_text, strip_jd_header, load_rows

YEARS_RE = re.compile(r'(\d{1,2})\s*\+?\s*(?:or more )?years', re.I)
YEARS_CTX = re.compile(r'program|project|technical|industry|hardware|engineering|management|experience|data|science|software')


def terms_in(text, vocab):
    low = text.lower()
    return [v['id'] for v in vocab if any(re.search(p, low) for p in v['patterns'])]


def min_years(text):
    ys = []
    for m in YEARS_RE.finditer(text):
        ctx = text[max(0, m.start() - 60): m.end() + 80].lower()
        if YEARS_CTX.search(ctx):
            y = int(m.group(1))
            if 2 <= y <= 25:
                ys.append(y)
    return min(ys) if ys else None


def data_path(c):
    return os.path.join(c.state_dir(), 'skill_gap_data.json')


def load_jds(c):
    docs, seen_h, skipped = [], set(), []
    apps = tracker.load(c)['applications']
    applied = {os.path.basename(a['jd_file']).lower() for a in apps if a.get('jd_file') and a.get('applied')}
    for root, _, files in os.walk(c.p('job_descriptions')):
        for f in sorted(files):
            low = f.lower()
            if low.startswith('_superseded') or low.endswith('.tmp') or not low.endswith(('.txt', '.md', '.docx', '.pdf')):
                continue
            try:
                t = read_text(os.path.join(root, f))
            except Exception as e:
                skipped.append((f, str(e))); continue
            if t is None:
                skipped.append((f, 'pdf, pdftotext not installed')); continue
            t = strip_jd_header(t)
            h = hashlib.md5(re.sub(r'\s+', ' ', t.lower()).strip().encode()).hexdigest()
            if h in seen_h or len(t) < 400:
                skipped.append((f, 'duplicate or too short')); continue
            seen_h.add(h)
            docs.append(dict(name=f, text=t, applied=low in applied))
    return docs, skipped


def master_text(c):
    p = c.p('master_resume')
    return (read_text(p) or '', os.path.basename(p)) if os.path.exists(p) else ('', 'not found')


def status_for(v, mtext, nc):
    low = mtext.lower()
    if any(re.search(p, low) for p in v['patterns']):
        return 'Claimed', ''
    key = (v.get('claim_term') or '').lower()
    if key:
        for n in nc:
            if n['term'].lower() == key or key in [x.lower() for x in n.get('aliases', [])]:
                return 'Decided no', n.get('reason', '')
    return 'Gap', ''


def ingest(c, scored_path, run, min_score=65):
    vocab = c.get('skill_vocabulary', [])
    data = read_json(data_path(c), {'schema_version': '1.0', 'postings': {}})
    n = 0
    for r in load_rows(scored_path):
        if (r.get('score') or 0) < min_score:
            continue
        text = (r.get('title') or '') + '\n' + (r.get('desc') or '')
        data['postings'][seen.job_key(r)] = dict(run=int(run), score=r.get('score'), terms=terms_in(text, vocab), min_years=min_years(r.get('desc') or ''))
        n += 1
    write_json(data_path(c), data)
    return n, len(data['postings'])


def report(c, out_dir=None):
    vocab = c.get('skill_vocabulary', [])
    if not vocab:
        raise ValueError('config.skill_vocabulary is empty: list the skills and tools your target roles ask for (see docs/CONFIG.md).')
    docs, skipped = load_jds(c)
    mtext, mname = master_text(c)
    nc = c.get('do_not_claim', [])
    data = read_json(data_path(c), {'postings': {}})
    runs = list(data['postings'].values())
    N, M = len(docs), len(runs)
    cnt, cnt_app, cnt_run = collections.Counter(), collections.Counter(), collections.Counter()
    for d in docs:
        d['terms'], d['years'] = terms_in(d['text'], vocab), min_years(d['text'])
        cnt.update(d['terms'])
        if d['applied']:
            cnt_app.update(d['terms'])
    for r in runs:
        cnt_run.update(r.get('terms') or [])
    rows = []
    for v in vocab:
        st, why = status_for(v, mtext, nc)
        pct = 100.0 * cnt[v['id']] / max(1, N)
        pr = 100.0 * cnt_run[v['id']] / M if M else None
        rows.append(dict(id=v['id'], label=v['label'], cat=v.get('category', ''), n=cnt[v['id']], pct=pct, n_app=cnt_app[v['id']], n_run=cnt_run[v['id']], pct_run=pr, status=st, why=why))
    rows.sort(key=lambda r: -(r['pct'] if r['pct_run'] is None else (r['pct'] + r['pct_run']) / 2))
    gaps = [r for r in rows if r['status'] != 'Claimed' and r['pct'] >= 10]
    ys = [d['years'] for d in docs if d['years']] + [r['min_years'] for r in runs if r.get('min_years')]
    yinfo = dict(n=len(ys), median=statistics.median(ys), p75=sorted(ys)[int(0.75 * (len(ys) - 1))], ge10=sum(1 for y in ys if y >= 10), mx=max(ys)) if ys else None
    summary = dict(generated=date.today().isoformat(), jds=N, applied_jds=sum(1 for d in docs if d['applied']), strong_fit_postings=M, master=mname, skipped=len(skipped), rows=rows, years=yinfo)
    out_dir = out_dir or c.p('search')
    os.makedirs(out_dir, exist_ok=True)
    write_json(os.path.join(out_dir, 'skill_gap_report.json'), summary)
    path = os.path.join(out_dir, 'skill_gap_report.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(render(summary, gaps))
    lines = ['corpus: %d saved JDs (%d applied) + %d strong-fit scraped postings | master resume: %s' % (N, summary['applied_jds'], M, mname),
             'Top gaps (asked in 10%+ of JDs, not claimed on the master resume):']
    for r in sorted(gaps, key=lambda r: -r['pct'])[:12]:
        lines.append('  %-46s %3.0f%% (%d/%d)  %s%s' % (r['label'], r['pct'], r['n'], N, r['status'], ' - ' + r['why'][:70] if r['why'] else ''))
    if not gaps:
        lines.append('  none')
    if yinfo:
        lines.append('Years asked (lowest stated per posting, n=%d): median %s, 75th percentile %s, %d ask for 10+' % (yinfo['n'], yinfo['median'], yinfo['p75'], yinfo['ge10']))
    lines.append('wrote ' + path)
    return lines, path


def render(S, gaps):
    e = H.escape
    bar = lambda p: '<span class="bar"><i style="width:%d%%"></i></span>' % min(100, round(p))
    trs = []
    for r in S['rows']:
        cls = {'Claimed': 'ok', 'Decided no': 'no', 'Gap': 'gap'}[r['status']]
        run = '' if r['pct_run'] is None else '%d / %d (%.0f%%)' % (r['n_run'], S['strong_fit_postings'], r['pct_run'])
        trs.append('<tr><td>%s</td><td class="mut">%s</td><td>%s %d / %d (%.0f%%)</td><td class="mut">%s</td><td class="num">%d</td><td><span class="tag %s">%s</span></td><td class="mut">%s</td></tr>' % (
            e(r['label']), e(r['cat']), bar(r['pct']), r['n'], S['jds'], r['pct'], run, r['n_app'], cls, r['status'], e(r['why'])))
    gl = ''.join('<li><b>%s</b>: asked in %.0f%% of saved JDs. %s</li>' % (e(r['label']), r['pct'],
                 ('You decided not to claim it (%s).' % e(r['why'])) if r['status'] == 'Decided no' else 'Not on the master resume and no decision recorded: claim it only if true, or build it.')
                 for r in sorted(gaps, key=lambda r: -r['pct'])[:10]) or '<li>No gaps above 10%.</li>'
    y = S['years']
    ytxt = '' if not y else '<p>Years asked (lowest stated per posting, n=%d): median %s, 75th percentile %s, %d ask for 10+, highest %s.</p>' % (y['n'], y['median'], y['p75'], y['ge10'], y['mx'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skill-gap report</title>
<style>:root{--bg:#f6f8fa;--s:#fff;--t:#1f2328;--m:#656d76;--l:#d0d7de;--a:#0969da;--g:#1a7f37;--r:#d1242f;--am:#9a6700}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--s:#161b22;--t:#e6edf3;--m:#8b949e;--l:#30363d;--a:#58a6ff;--g:#3fb950;--r:#f85149;--am:#d29922}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--t);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}.w{max-width:1200px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--m);font-size:13px;margin-bottom:16px}.t{overflow-x:auto}table{width:100%%;border-collapse:collapse;background:var(--s);border:1px solid var(--l);min-width:760px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--l);vertical-align:top}th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--m)}
.mut{color:var(--m);font-size:12px}.num{text-align:right}.bar{display:inline-block;width:70px;height:8px;background:var(--l);border-radius:4px;margin-right:6px;vertical-align:middle}
.bar i{display:block;height:8px;background:var(--a);border-radius:4px}.tag{padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600}
.ok{background:rgba(26,127,55,.15);color:var(--g)}.no{background:rgba(154,103,0,.18);color:var(--am)}.gap{background:rgba(209,36,47,.15);color:var(--r)}
.card{background:var(--s);border:1px solid var(--l);border-radius:6px;padding:12px 16px;margin-bottom:16px}li{margin:4px 0}</style></head><body><div class="w">
<h1>Skill-gap report</h1><div class="sub">Generated %s from %d saved job descriptions (%d you applied to) and %d strong-fit scraped postings. Master resume: %s. %d files skipped (duplicates, superseded copies, unreadable).</div>
<div class="card"><b>Biggest gaps</b> (asked in 10%%+ of saved JDs, not claimed on the master resume)<ul>%s</ul>%s</div>
<div class="t"><table><thead><tr><th>Requirement</th><th>Type</th><th>Saved JDs</th><th>Strong-fit scrapes</th><th class="num">Applied JDs</th><th>Your status</th><th>Why</th></tr></thead><tbody>%s</tbody></table></div>
<p class="mut">Status is read from your own files: Claimed = the term appears in the master resume; Decided no = it is on your do-not-claim list; Gap = neither. Counts are keyword matches, so read a hit as "mentioned", not "required". Saved JDs are roles you chose to look at, so they lean toward your target, not toward the whole market.</p></div></body></html>''' % (
        S['generated'], S['jds'], S['applied_jds'], S['strong_fit_postings'], e(S['master']), S['skipped'], gl, ytxt, ''.join(trs))
