"""Turn the config into the searches to run: LinkedIn URLs (general and per company), Indeed and Glassdoor queries,
batches, and an optional multi-day plan. The suite never connects to a source itself; the skill runs these
through whatever connectors the candidate has set up."""
import os
from urllib.parse import quote, quote_plus
from jobsearch.util import norm, read_json, write_json, hit


def dedicated_companies(c):
    """Companies that get their own LinkedIn query: tiers in companies.dedicated_query_tiers, tier order then config order."""
    want = set(int(t) for t in c['companies'].get('dedicated_query_tiers', [1, 2]))
    out = []
    for t, name, aliases in c.tiers():
        if t in want:
            out.append(name)
    return out


def batches(c):
    size = max(1, int(c['sources']['linkedin'].get('company_batch_size', 5)))
    names = dedicated_companies(c)
    return {'B%d' % (i // size + 1): names[i:i + size] for i in range(0, len(names), size)}


def batch_of(c, company):
    """Which batch holds this company, or None (it is covered by the general queries only)."""
    n = norm(company)
    for label, names in batches(c).items():
        for nm in names:
            if hit(norm(nm), n) or hit(n, norm(nm)):
                return label
    return None


def linkedin_url(c, keywords, f_wt):
    li = c['sources']['linkedin']
    return '%s&keywords=%s&f_WT=%s' % (li['search_url'], quote_plus(keywords), quote(f_wt, safe=''))


def general_urls(c):
    return [(q['id'], linkedin_url(c, q['keywords'], q.get('f_WT', '1,2,3'))) for q in c['sources']['linkedin']['general_queries']]


def company_urls(c, label):
    li = c['sources']['linkedin']
    return [(nm, linkedin_url(c, li['company_query'].replace('{company}', nm), li.get('company_f_WT', '1,2,3'))) for nm in batches(c).get(label, [])]


def plan(c):
    """Stages. With staging.enabled: general queries + Indeed + the first batches on day 1, then a few batches a day,
    other boards last. Otherwise one stage with everything."""
    bl = list(batches(c))
    boards = [s for s in ('indeed', 'glassdoor', 'dice') if c['sources'].get(s, {}).get('enabled')]
    if not c.get('staging', {}).get('enabled'):
        return [{'stage': 1, 'items': ['GroupA'] + bl + [b.capitalize() for b in boards]}]
    per = max(1, int(c['staging'].get('batches_per_day', 2)))
    stages = [{'stage': 1, 'items': ['GroupA'] + (['Indeed'] if 'indeed' in boards else []) + bl[:per]}]
    rest = bl[per:]
    for i in range(0, len(rest), per):
        stages.append({'stage': len(stages) + 1, 'items': rest[i:i + per]})
    other = [b.capitalize() for b in boards if b != 'indeed']
    if other:
        stages[-1]['items'] += other
    return stages


def state_path(c):
    return os.path.join(c.state_dir(), 'staged_run.json')


def mark(c, label, status='DONE', date=''):
    st = read_json(state_path(c), {'batches': {}})
    st.setdefault('batches', {})[label] = {'status': status, 'date': date}
    write_json(state_path(c), st)


def status_map(c):
    st = read_json(state_path(c), {'batches': {}})
    return {k: (v.get('status') if isinstance(v, dict) else str(v)).upper() for k, v in st.get('batches', {}).items()}


def render(c, source='all', batch=None, pending=False):
    """Plain-text listing of queries."""
    out = []
    done = status_map(c) if pending else {}
    if source in ('all', 'linkedin') and c['sources']['linkedin'].get('enabled'):
        if batch in (None, 'A', 'GroupA'):
            if not (pending and done.get('GroupA') == 'DONE'):
                out.append('# LinkedIn general queries (GroupA)')
                out += ['%s  %s' % (i, u) for i, u in general_urls(c)]
        for label in batches(c):
            if batch not in (None, label) or (pending and done.get(label) == 'DONE'):
                continue
            out.append('# LinkedIn %s: %s' % (label, ', '.join(batches(c)[label])))
            out += ['%s  %s' % (n, u) for n, u in company_urls(c, label)]
    if source in ('all', 'indeed') and c['sources'].get('indeed', {}).get('enabled'):
        out.append('# Indeed searches')
        out += ['%s | %s' % (s['keywords'], s['location']) for s in c['sources']['indeed']['searches']]
    if source in ('all', 'glassdoor') and c['sources'].get('glassdoor', {}).get('enabled'):
        out.append('# Glassdoor queries')
        out += ['%s | %s | max %s' % (q['keyword'], q['location'], q.get('maxJobs', 20)) for q in c['sources']['glassdoor']['queries']]
    if source in ('all', 'dice') and c['sources'].get('dice', {}).get('enabled'):
        out.append('# Dice queries')
        out += ['%s | %s' % (q.get('keyword', ''), q.get('location', '')) for q in c['sources']['dice'].get('queries', [])]
    return '\n'.join(out)
