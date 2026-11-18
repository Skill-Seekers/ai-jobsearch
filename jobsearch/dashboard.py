"""Build the HTML dashboard (always) and the CSV report (when outputs.csv is true or --csv is passed)."""
import csv, glob, json, os, re
from datetime import datetime, timedelta
from jobsearch import tracker
from jobsearch.score import BUCKETS
from jobsearch.util import load_rows

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'dashboard_template.html')
FORMULA = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(v):
    """Neutralise spreadsheet formulas: a scraped title that starts with = + - @ must never run as one."""
    s = '' if v is None else str(v)
    return ("'" + s) if s.startswith(FORMULA) else s


def next_run_number(c, day):
    """Runs already on disk + 1. Re-building the same day's dashboard keeps that day's number."""
    files = glob.glob(os.path.join(c.p('search'), 'job_search_*.html'))
    prior = [f for f in files if os.path.basename(f) != 'job_search_%s.html' % day]
    return len(prior) + 1


def _salary(r):
    return r.get('salary') or 'Not listed'


def build(c, scored_path, dropped_paths, run=None, day=None, sources=None, unavailable=None, mode='full', notes='', csv_out=None, out_dir=None):
    day = day or datetime.now().strftime('%Y-%m-%d')
    run = int(run) if run else next_run_number(c, day)
    out_dir = out_dir or c.p('search')
    os.makedirs(out_dir, exist_ok=True)
    cutoff = (datetime.strptime(day, '%Y-%m-%d') - timedelta(days=c['scoring']['new_badge_days'])).strftime('%Y-%m-%d')
    apps = tracker.load(c)['applications']
    rows = load_rows(scored_path)
    keep = [r for r in rows if r.get('bucket') in BUCKETS]
    keep.sort(key=lambda r: r.get('posted') or '', reverse=True)                      # newest first among equal scores
    keep.sort(key=lambda r: (BUCKETS.index(r['bucket']), -r['score']))
    results = []
    for i, r in enumerate(keep, 1):
        title = re.sub(r'\s*\U0001F195', '', r['title']).strip()
        is_new = bool(r.get('posted')) and r['posted'] >= cutoff
        a = tracker.match(r['company'], title, apps, r.get('link', ''), generic=tracker.generic_words(c))
        reason = (r.get('adjustments') or [{}])[-1].get('reason') or ', '.join(r.get('why', []))
        results.append(dict(num=i, match=r['score'], bucket=r['bucket'], source=r.get('source') or 'Other', company=r['company'], title=title,
                            workMode=r.get('workMode', ''), employment=r.get('employment', ''), applicants=r.get('applicants') or 0, location=r.get('location', ''),
                            posted=r.get('posted', ''), salary=_salary(r), link=r.get('link', ''), note=r.get('note', ''), is_new=is_new, why=reason,
                            applied_id=(a or {}).get('id', ''), applied_status=(a or {}).get('status', '') if a else ''))
    for r in results:                                     # the NEW flag is derived in code and checked, never typed by hand
        assert r['is_new'] == (bool(r['posted']) and r['posted'] >= cutoff)
    filtered = []
    for p in dropped_paths:
        for d in load_rows(p) or []:
            filtered.append(dict(company=d.get('company', ''), title=d.get('title', ''), location=d.get('location', ''), posted=d.get('posted', ''),
                                 reasonType=d.get('reasonType', 'wrong'), reason=d.get('reason', ''), link=d.get('link', '')))
    for r in rows:
        if r.get('bucket') == 'Filtered':
            filtered.append(dict(company=r['company'], title=r['title'], location=r.get('location', ''), posted=r.get('posted', ''), reasonType='wrong',
                                 reason='Scored %d%%, below the %d%% floor (%s)' % (r['score'], c['scoring']['hard_floor'], ', '.join(r.get('why', []))), link=r.get('link', '')))
    sources = sources or sorted({r['source'] for r in results}) or ['none']
    label = ('Quick run, partial coverage' if mode == 'quick' else '%d-day window' % c['scoring']['posted_within_days'])
    footer = 'Run #%d · %s · %s · Sources: %s' % (run, day, label, ', '.join(sources))
    if unavailable:
        footer += ' · Unavailable this run: %s' % ', '.join(unavailable)
    footer += ' · Scores are a keyword heuristic, not a forecast. Confirm a posting is open before applying.'
    data = dict(run=run, date=day, new_days=c['scoring']['new_badge_days'], filter_label=label, sources_label=' · '.join(sources), footer=footer, notes=notes, results=results,
                filtered=filtered, applications=tracker.rows_for_dashboard(c, day))
    blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    html = open(ASSET, encoding='utf-8').read()
    heading = '%s · Job Search' % c['candidate']['name'] if c['candidate'].get('name') else 'Job Search'
    esc = lambda t: t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    for k, v in (('__TITLE__', esc('Job Search Dashboard | Run #%d | %s' % (run, day))), ('__HEADING__', esc(heading)), ('__NOTES_ID__', 'RUN NOTES'), ('__DATA__', blob)):
        html = html.replace(k, v)                          # __DATA__ last, so text inside the data can never be mistaken for a placeholder
    for leftover in ('__TITLE__', '__HEADING__', '__DATA__', '__NOTES_ID__'):
        assert leftover not in html, 'template placeholder left behind: ' + leftover
    path = os.path.join(out_dir, 'job_search_%s.html' % day)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    out = dict(html=path, results=len(results), filtered=len(filtered), run=run)
    if csv_out is True or (csv_out is None and c['outputs'].get('csv')):
        cp = os.path.join(out_dir, 'job_search_%s.csv' % day)
        with open(cp, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Rank', 'Match', 'Bucket', 'Company', 'Title', 'Location', 'Work mode', 'Posted', 'Salary', 'Source', 'Recently posted', 'In tracker', 'Note', 'Link'])
            for r in results:
                w.writerow([csv_safe(x) for x in (r['num'], r['match'], r['bucket'], r['company'], r['title'], r['location'], r['workMode'], r['posted'], r['salary'],
                                                 r['source'], 'yes' if r['is_new'] else '', r['applied_status'], r['note'], r['link'])])
        out['csv'] = cp
    return out
