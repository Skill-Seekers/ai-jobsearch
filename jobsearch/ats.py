"""ATS check for a resume (.docx): can a parser read it, and which job-description keywords are missing?

Formatting guidance only. It does not predict any employer's ATS ranking. It never inserts anything: missing
keywords are reported as gaps for the candidate to decide on. A gap on the candidate's do_not_claim list is
marked DO NOT ADD, and a do_not_claim term found inside the resume is flagged."""
import collections, os, re
from jobsearch.util import docx_paragraphs, read_text, strip_jd_header, W

STOP = set("""a an and are as at be been being but by can could do does for from had has have he her his i if in into is it its may me more most must my no not of on one or our out over per should so such than that the their them then there these they this those to up us was we were what when where which who will with within would you your
usd salary base linkedin row req reqs match score job distinct pay range compensation benefits eligible equity stock bonus experience experiences ability able work working works role roles team teams strong including include includes etc years year plus preferred required requirements responsibilities qualifications minimum bachelor degree related field equivalent new key across using use used based well good great excellent skills skill knowledge understanding looking join company position candidate candidates opportunity employer equal national origin status veteran disability gender race color religion sex age sexual orientation saved""".split())

# Generic job-description terms come from config (ats_generic_terms); see docs/ADAPTING.md.


def inspect(path):
    root, paras, z = docx_paragraphs(path)
    info = dict(paragraphs=paras, tables=len(list(root.iter(W + 'tbl'))), textboxes=len(list(root.iter(W + 'txbxContent'))),
                images=len(list(root.iter(W + 'drawing'))) + len(list(root.iter(W + 'pict'))), header='', footer='')
    info['table_chars'] = sum(len(t.text or '') for tb in root.iter(W + 'tbl') for t in tb.iter(W + 't'))
    import xml.etree.ElementTree as ET
    for name in z.namelist():
        kind = 'header' if re.match(r'word/header\d*\.xml', name) else 'footer' if re.match(r'word/footer\d*\.xml', name) else None
        if kind:
            r = ET.fromstring(z.read(name))
            info[kind] += ' '.join(''.join(t.text or '' for t in p.iter(W + 't')) for p in r.iter(W + 'p')) + ' '
    return info


def words(text):
    return re.findall(r"[a-z][a-z0-9+#/&.-]*[a-z0-9+#]|[a-z]", text.lower())


def stem(w):
    w = w.lower().strip('.-/&')
    for suf in ('ing', 'ed', 'es', 's'):
        if len(w) > 5 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def domain_patterns(c):
    pats = list(c.get('ats_generic_terms', []))
    for v in c.get('skill_vocabulary', []):
        pats += v.get('patterns', [])
    return pats


def jd_terms(jd, pats):
    low = jd.lower()
    terms = collections.Counter()
    for pat in pats:
        for mm in re.finditer(pat, low):
            terms[re.sub(r'\\b|\\w\*|\\w\+|\?', '', mm.group(0)).strip()] += 1
    for a in re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', jd):
        if a.lower() not in ('and', 'the', 'for', 'usa', 'inc', 'llc', 'eeo'):
            terms[a.lower()] += 2
    toks = words(low)
    for n in (2, 3):
        grams = collections.Counter()
        for i in range(len(toks) - n + 1):
            g = toks[i:i + n]
            if g[0] in STOP or g[-1] in STOP or any(len(x) < 3 for x in (g[0], g[-1])):
                continue
            grams[' '.join(g)] += 1
        for g, cnt in grams.items():
            if cnt >= 2:
                terms[g] += cnt
    return terms


def present(term, low, stems):
    if term in low:
        return True
    parts = [stem(p) for p in re.split(r'[\s/]+', term) if p]
    if len(parts) == 1:
        if parts[0] in stems:
            return True
        root = parts[0][:-3] if len(parts[0]) > 7 else ''          # 'escalation' is covered by 'escalated'
        return bool(root) and any(w.startswith(root) for w in stems)
    return ' '.join(parts) in ' '.join(stem(w) for w in words(low))


def check(c, resume, jd_path):
    """Returns (markdown text, summary dict)."""
    info = inspect(resume)
    body = '\n'.join(p for p in info['paragraphs'] if p.strip())
    full = body + '\n' + info['header'] + '\n' + info['footer']
    jd = strip_jd_header(read_text(jd_path) or '')
    low = full.lower()
    stems = {stem(w) for w in words(low)}
    lines = [p.strip() for p in info['paragraphs'] if p.strip()]
    email = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', full)
    phone = re.search(r'(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', full)
    short = [l.lower() for l in lines if len(l) < 60]
    heads = {'Experience': any(re.search(r'^(professional |work |prior )?experience', l) for l in short),
             'Education': any(re.search(r'^education', l) for l in short),
             'Skills': any(re.search(r'^(core |technical |key )?(skills|competencies)|^areas of expertise|^technical depth', l) for l in short)}
    std_skills = any(re.search(r'^(core |technical |key )?(skills|competencies)\b', l) for l in short)
    L, P = [], None
    P = L.append
    P('# ATS check: %s vs %s' % (os.path.basename(resume), os.path.basename(jd_path)))
    P('\nFormatting guidance only. It does not predict any employer\'s ATS ranking.')
    P('\n## 1. Can a parser read it?')
    P('- Name line: "%s"' % (lines[0][:60] if lines else 'MISSING'))
    P('- Email: %s | Phone: %s' % ('ok' if email else 'MISSING', 'ok' if phone else 'MISSING'))
    P('- Section headings: %s' % ', '.join('%s %s' % (k, 'ok' if v else 'NOT FOUND') for k, v in heads.items()))
    warns = []
    if info['textboxes']:
        warns.append('%d text box(es): many ATS skip text boxes. Move that text into the body.' % info['textboxes'])
    if info['images']:
        warns.append('%d image/drawing object(s): an ATS cannot read images.' % info['images'])
    if info['tables']:
        warns.append('%d table(s) hold %.0f%% of the text. Most parsers read tables cell by cell; check the order still makes sense.' % (info['tables'], 100.0 * info['table_chars'] / max(1, len(body))))
    if email and email.group(0).lower() in (info['header'] + info['footer']).lower():
        warns.append('Contact details sit in the header/footer. Some ATS ignore headers; repeat them in the body.')
    if not (email and phone):
        warns.append('Contact details incomplete in the text layer.')
    for k in ('Experience', 'Education', 'Skills'):
        if not heads[k]:
            warns.append('No "%s" heading found; parsers need a plain heading to file that section.' % k)
    P('- Structure warnings: %s' % ('none' if not warns else ''))
    P('\n'.join('  - ' + w for w in warns)) if warns else None
    if heads['Skills'] and not std_skills:
        P('- Note: the skills section is not headed "Skills" or "Core Competencies"; those are the safest labels.')
    P('- Length: %d words, %d paragraphs' % (len(words(body)), len(lines)))

    P('\n## 2. Job-description keyword coverage (gaps are reported, never inserted)')
    nc = c.get('do_not_claim', [])
    company_word = re.split(r'[_ -]', os.path.basename(jd_path))[0].lower()
    terms = jd_terms(jd, domain_patterns(c))
    ranked = [t for t, _ in terms.most_common(120) if t not in STOP and len(t) > 2 and company_word not in t.split() and not re.search(r'\d{4,}|^(jr|req)\d+', t)]
    singles = [t for t in ranked if ' ' not in t]
    ranked = [t for t in ranked if not (' ' not in t and any(u != t and u.startswith(t) for u in singles))]      # 'escalat' and 'escalation' are one term
    covered, missing = [], []
    for t in ranked:
        if len(covered) + len(missing) >= 45:
            break
        (covered if present(t, low, stems) else missing).append(t)
    tot = len(covered) + len(missing)
    pct = 100.0 * len(covered) / max(1, tot)
    P('- Coverage: %d of the top %d terms present (%.0f%%)' % (len(covered), tot, pct))
    P('- Covered: ' + (', '.join(covered) or 'none'))
    P('- Terms are ranked by frequency in the posting plus your skill vocabulary. Judge each gap yourself; many are not real requirements.')
    P('\n### Gaps')
    blocked = []
    open_gaps = 0
    for t in missing:
        hit = next((n for n in nc if t == n['term'].lower() or t in [x.lower() for x in n.get('aliases', [])]), None)
        if hit:
            blocked.append((t, hit.get('reason', '')))
        else:
            P('- ' + t)
            open_gaps += 1
    if not open_gaps:
        P('- none outside your do-not-claim list')
    jl = jd.lower()
    for n in nc:
        names = [n['term'].lower()] + [x.lower() for x in n.get('aliases', [])]
        if any(x in jl for x in names) and not present(n['term'].lower(), low, stems) and n['term'].lower() not in [b[0] for b in blocked]:
            blocked.append((n['term'].lower(), n.get('reason', '')))
    if blocked:
        P('\n### DO NOT ADD (the posting asks, you have decided not to claim it)')
        for t, r in blocked:
            P('- %s: %s' % (t, r))
    P('\n## 3. Do-not-claim guard')
    bad = []
    for n in nc:
        for k in [n['term']] + n.get('aliases', []):
            if re.search(r'(?<![a-z0-9])' + re.escape(k.lower()) + r'(?![a-z0-9])', low):
                bad.append((k, n.get('reason', '')))
                break
    if bad:
        P('- WARNING: the resume contains terms on your do-not-claim list:')
        for k, r in bad:
            P('  - "%s": %s' % (k, r))
    else:
        P('- ok: no do-not-claim terms found in the resume text')
    return '\n'.join(L) + '\n', dict(coverage=round(pct), warnings=len(warns), gaps=open_gaps, blocked=len(blocked), claimed_violations=len(bad))
