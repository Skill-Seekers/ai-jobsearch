"""Merge raw search rows from every source, de-duplicate, apply the date window and the exclusions.

Input: a folder of *.json files, each a list of rows or {"items": [...]}. Rows use the field names of the
LinkedIn actor (companyName, title, location, postedAt, applicantsCount, salary, employmentType,
seniorityLevel, link, descriptionText); common aliases are accepted. Add "_source" to say where a row came from;
otherwise it is guessed from the link. Output: keep.json and dropped.json (see docs/DATA_SCHEMAS.md)."""
import collections, glob, os, re
from datetime import datetime, timedelta
from jobsearch.util import load_rows, write_json, norm_simple, norm

SOURCE_PRIORITY = ['LinkedIn', 'Indeed', 'Google Jobs', 'Glassdoor', 'Dice', 'Other']


def guess_source(row):
    s = row.get('_source') or row.get('source')
    if s:
        return s
    link = (row.get('link') or row.get('url') or '').lower()
    for key, name in (('linkedin.', 'LinkedIn'), ('indeed.', 'Indeed'), ('glassdoor.', 'Glassdoor'), ('dice.', 'Dice'), ('google.', 'Google Jobs')):
        if key in link:
            return name
    return 'Other'


def first(row, *names):
    for n in names:
        if row.get(n) not in (None, ''):
            return row[n]
    return ''


def parse_salary(text):
    """(low, high) integers from '$150,000 - $210,000' or '$150K-$210K'; (None, None) if nothing usable."""
    vals = []
    for m in re.finditer(r'\$\s?([\d,]+(?:\.\d+)?)\s?([kK])?', text or ''):
        v = float(m.group(1).replace(',', ''))
        if m.group(2):
            v *= 1000
        if v >= 1000:
            vals.append(int(v))
    if not vals:
        return None, None
    return min(vals), max(vals)


def is_remote(row):
    return 'remote' in (row.get('location') or '').lower() or 'remote' in (row.get('desc') or '')[:400].lower()


def is_home(row, c):
    loc = (row.get('location') or '').lower()
    return any(k in loc for k in c['scoring'].get('home_locations', []))


def clean_link(link):
    """Drop tracking parameters but keep the posting id Indeed carries in ?jk=."""
    m = re.search(r'[?&](jk=[0-9a-fA-F]{8,})', link)
    base = link.split('?')[0]
    return base + '?' + m.group(1) if m else base


def normalise(item):
    posted = str(first(item, 'postedAt', 'posted', 'datePosted', 'date') or '')[:10]
    if not re.match(r'\d{4}-\d{2}-\d{2}$', posted):
        posted = ''
    apps = re.sub(r'\D', '', str(first(item, 'applicantsCount', 'applicants') or '0')) or '0'
    return dict(source=guess_source(item), company=str(first(item, 'companyName', 'company')).strip(), title=str(first(item, 'title')).strip(),
                location=str(first(item, 'location')).strip(), posted=posted, applicants=int(apps),
                salary=str(first(item, 'salary')).strip(), employment=str(first(item, 'employmentType', 'employment')).strip(),
                seniority=str(first(item, 'seniorityLevel', 'seniority')).strip(),
                link=clean_link(str(first(item, 'link', 'url'))), desc=str(first(item, 'descriptionText', 'description', 'desc'))[:4500])


def dedupe_key(r):
    m = re.search(r'/jobs/view/[^?]*?(\d{8,12})', r['link'])
    if m:
        return ('li', m.group(1))
    m = re.search(r'[?&]jk=([0-9a-f]{8,})', r['link'])
    if m:
        return ('in', m.group(1))
    return ('t', re.sub(r'[^a-z0-9]', '', r['company'].lower()), ' '.join(norm_simple(r['title']).split()[:6]), re.sub(r'[^a-z]', '', r['location'].lower())[:14])


def run(c, raw_dir, today, out_dir):
    today_d = datetime.strptime(today, '%Y-%m-%d').date()
    days = c['scoring']['posted_within_days']
    cut = (today_d - timedelta(days=days)).isoformat()
    raw = []
    for f in sorted(glob.glob(os.path.join(raw_dir, '*.json'))):
        for item in load_rows(f) or []:
            r = normalise(item)
            if r['company'] and r['title']:
                raw.append(r)
    raw.sort(key=lambda r: SOURCE_PRIORITY.index(r['source']) if r['source'] in SOURCE_PRIORITY else 99)   # best source first
    rows, seen_t = {}, {}
    for r in raw:
        k = dedupe_key(r)
        if k in rows:
            continue
        tk = ('t', re.sub(r'[^a-z0-9]', '', r['company'].lower())[:6], ' '.join(norm_simple(r['title']).split()[:6]), r['location'].split(',')[0].strip().lower())
        if k[0] != 'li' and tk in seen_t:      # same role from a lower-priority source
            continue
        rows[k] = r
        seen_t[tk] = True
    inwin = [r for r in rows.values() if (not r['posted']) or r['posted'] >= cut]
    keep, dropped = [], []
    buckets = collections.Counter()
    bad_titles = [norm(t) for t in c.get('title_exclusions', [])]
    floor = c['targets']['compensation'].get('hard_drop_below_max')
    action = c['targets'].get('out_of_area_action', 'filter')
    for r in inwin:
        ex = c.excluded(r['company'])
        if ex:
            buckets['excluded-company'] += 1
            if ex[2] != 'silent':
                dropped.append(dict(cat='COMPANY', reasonType=ex[0], reason=ex[1], **r))
            continue
        tl = norm(r['title'])
        if any(re.search(r'(?<![a-z0-9])' + re.escape(b) + r'(?![a-z0-9])', tl) for b in bad_titles if b):
            buckets['title'] += 1
            dropped.append(dict(cat='TITLE', reasonType='wrong', reason='Wrong title for the target roles.', **r)); continue
        lo, hi = parse_salary(r['salary'])
        if floor and hi and hi < floor:
            buckets['salary'] += 1
            dropped.append(dict(cat='PAY', reasonType='wrong', reason='Listed maximum $%s is below the hard floor ($%s).' % (format(hi, ','), format(floor, ',')), **r)); continue
        if action == 'filter' and not is_remote(r) and not is_home(r, c):
            buckets['location'] += 1
            dropped.append(dict(cat='LOCATION', reasonType='wrong', reason='Outside the preferred area and not remote (no relocation).', **r)); continue
        if not r['posted']:
            r['note'] = 'Posting date unknown: confirm it is recent.'
        keep.append(r)
    os.makedirs(out_dir, exist_ok=True)
    write_json(os.path.join(out_dir, 'keep.json'), keep)
    write_json(os.path.join(out_dir, 'dropped.json'), dropped)
    return dict(raw=len(raw), unique=len(rows), in_window=len(inwin), kept=len(keep), dropped=len(dropped), cut=cut, buckets=dict(buckets))
