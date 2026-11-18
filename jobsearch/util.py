"""Small shared helpers: text normalisation, JSON, reading .docx/.txt/.md, JD header stripping."""
import json, os, re, shutil, subprocess, zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def norm(s):
    """Lower-case, punctuation to spaces, collapsed. Used for company and title comparison."""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 &.+-]', ' ', (s or '').lower())).strip()


def norm_simple(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower())).strip()


def hit(key, normalised):
    """Short keys (4 characters or fewer) must match a whole word ('abc' must not hit 'abcdef')."""
    key = (key or '').strip().lower()
    if not key:
        return False
    if len(key) <= 4:
        return re.search(r'(?<![a-z0-9])' + re.escape(key) + r'(?![a-z0-9])', normalised) is not None
    return key in normalised


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, obj, indent=1):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, path)


def load_rows(path):
    """A list of row dicts from a JSON file that is a list or {"items": [...]}."""
    d = read_json(path)
    if isinstance(d, dict):
        d = d.get('items') or d.get('jobs') or d.get('rows') or []
    return d


def docx_paragraphs(path):
    """(root, paragraphs, zipfile) of word/document.xml; paragraph text includes tabs."""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read('word/document.xml'))
    out = []
    for p in root.iter(W + 'p'):
        out.append(''.join((n.text or '') if n.tag == W + 't' else '\t' for n in p.iter() if n.tag in (W + 't', W + 'tab')))
    return root, out, z


def read_text(path):
    """Text of .docx / .txt / .md / .pdf (pdf needs the pdftotext tool; returns None if it is missing)."""
    low = path.lower()
    if low.endswith('.docx'):
        return '\n'.join(docx_paragraphs(path)[1])
    if low.endswith('.pdf'):
        if not shutil.which('pdftotext'):
            return None
        try:
            return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, timeout=30).stdout
        except Exception:
            return None
    with open(path, encoding='utf-8', errors='ignore') as f:
        return f.read()


_META = re.compile(r'^\s*(title|location|source|posted|employment|match|score|reqs?|req id|captured|company|salary|compensation|link|url|recruiter|rate|agency|type|work mode|job id)\s*[:\-—].*$', re.I)


def strip_jd_header(text):
    """Saved JDs may start with a capture header (COMPANY:, TITLE:, SOURCE: ...), then a ==== line."""
    m = re.search(r'^={5,}\s*$', text[:3000], re.M)
    if m:
        text = text[m.end():]
    return '\n'.join(l for i, l in enumerate(text.split('\n')) if not (i < 20 and _META.match(l)))
