#!/usr/bin/env python3
"""Privacy gate for a repo you are about to publish. Python 3.8+, standard library only.

  privacy_scan.py build-denylist --out DENY.txt [--seed SEED.txt] [--tracker T.json]...
                                 [--resume FILE]... [--metrics FILE]...
        Builds the private list of terms that must never be published (your name, email, phone,
        employers, companies you applied to, requisition and posting IDs, resume numbers).
        Run it where your real files are. Keep the output OUTSIDE the repo. Never commit it.

  privacy_scan.py scan PATH --denylist DENY.txt [--report OUT.txt] [--strict] [--show]
        Scans every file under PATH, plus the inside of .docx/.xlsx/.pptx/.zip/.plugin files,
        file names, document metadata, image/PDF metadata and git history. Exit 0 = nothing
        found, 1 = findings (FAIL, or WARN with --strict), 2 = bad usage.

  privacy_scan.py manifest PATH [--out MANIFEST.txt] [--compare OLD_MANIFEST.txt]
        Lists every file with size and SHA-256 so a human can review exactly what will ship,
        and shows what was added, changed or removed since the last manifest.

  privacy_scan.py selftest
        Plants fictional leaks in a temporary tree and proves the scanner catches each one.

Denylist format, one entry per line:  CATEGORY|term     (# comment;  !term = exception)
  CATEGORY is any label (NAME, EMAIL, PHONE, EMPLOYER, COMPANY, PERSON, ID, PATH, OTHER...).
  METRIC and AMBIG entries are reported as WARN; everything else is FAIL.
  A term may be  re:<regex>  for a pattern. Multi-word terms also match Name_Name, NameName,
  and Name-Name, so file names are covered. Terms of 8+ characters match inside longer words;
  shorter terms match only as whole words, and a short capitalised term such as Globex is
  case-sensitive (so ordinary words and file names are not flagged).
Limits: it finds what it knows to look for. Images and PDFs are only partly inspectable, so they
are listed for you to open and check by eye. Read the manifest before every release.
"""
import argparse, hashlib, io, json, os, re, shutil, struct, subprocess, sys, tempfile, zipfile

WARN_CATS = {'METRIC', 'AMBIG'}
ZW = dict.fromkeys(map(ord, '\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u00ad'), None)
OOXML = {'.docx', '.xlsx', '.pptx', '.docm', '.xlsm', '.pptm', '.dotx', '.xltx', '.potx', '.odt', '.ods', '.odp'}
ARCHIVES = OOXML | {'.zip', '.plugin', '.jar', '.whl', '.skill'}
REVIEW = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.bmp', '.tif', '.tiff', '.ico', '.pdf',
          '.mp4', '.mov', '.mp3', '.wav', '.woff', '.woff2', '.ttf', '.otf'}
RISKY_NAMES = ('.env', 'id_rsa', 'id_ed25519', '.netrc', '.npmrc', '.pypirc')
RISKY_EXT = {'.pem', '.key', '.p12', '.pfx', '.keystore', '.sqlite', '.db', '.log', '.har'}
JUNK_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
JUNK_EXT = ('.bak', '.tmp', '.swp', '.orig', '.rej')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}
OK_AUTHORS = {'', 'python-docx', 'openpyxl', 'ai-jobsearch', 'unknown', 'anonymous', 'author', 'user', 'sample candidate'}
OK_EMAIL_DOMAINS = {'example.com', 'example.org', 'example.net', 'users.noreply.github.com', 'noreply.github.com'}
OK_EMAILS = {'noreply@anthropic.com'}
PLACEHOLDER = re.compile(r'(?i)(your|example|username|user-?name|firstname|lastname|first-?last|placeholder|changeme|xxxx|<|\{|\$\{|alex-?rivera|jane|john)')


# ------------------------------------------------------------------ denylist
def parse_denylist(path):
    entries, exceptions = [], set()
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('!'):
                exceptions.add(line[1:].strip().lower()); continue
            if '|' not in line:
                continue
            cat, term = line.split('|', 1)
            cat, term = cat.strip().upper(), term.strip()
            if term:
                entries.append((cat, term))
    entries = [(c, t) for c, t in entries if t.lower() not in exceptions]
    return entries


def term_regex(term):
    if term.startswith('re:'):
        return re.compile(term[3:], re.I)
    toks = [t for t in re.split(r'[\s_\-]+', term.strip()) if t]
    if not toks:
        return None
    body = r'[\s_\-.]{0,3}'.join(re.escape(t) for t in toks)
    if sum(len(t) for t in toks) >= 8:
        return re.compile(body, re.I)
    # short proper nouns (Globex, Initech, Contoso) are matched case-sensitively so that ordinary words
    # and file names (meta.xml, a lower-case word) are not flagged; ALL-CAPS and lower-case terms ignore case
    flags = 0 if re.match(r'^[A-Z][a-z]', toks[0]) else re.I
    return re.compile(r'(?<![A-Za-z0-9])' + body + r'(?![A-Za-z0-9])', flags)


def mask(s, show):
    s = s.strip()
    if show or len(s) <= 2:
        return s if show else '*' * len(s)
    return s[0] + '*' * (min(len(s), 12) - 1)


# ------------------------------------------------------------------ generic detectors
GENERIC = [
    ('SECRET', 'FAIL', re.compile(r'apify_api_[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9\-]{10,}|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('SECRET', 'FAIL', re.compile(r'(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-./+]{16,})')),
    ('PATH', 'FAIL', re.compile(r'[A-Za-z]:\\+Users\\+([^\\\s"\'<>|*?]+)')),
    ('PATH', 'FAIL', re.compile(r'/(?:Users|home)/([A-Za-z0-9._\-]+)/')),
    ('PATH', 'FAIL', re.compile(r'/sessions/[a-z0-9\-]{8,}|\bOneDrive\b')),
    ('LINKEDIN_PROFILE', 'FAIL', re.compile(r'linkedin\.com/in/[A-Za-z0-9_%\-]+', re.I)),
    ('POSTING', 'FAIL', re.compile(r'linkedin\.com/jobs/view/[^\s"\')<>]*\d{8,}|indeed\.com/[^\s"\')<>]*jk=[0-9a-f]{12,}|glassdoor\.[a-z.]+/job-listing/[^\s"\')<>]+', re.I)),
    ('REQ_ID', 'WARN', re.compile(r'\bJR\d{6,8}\b|\bR\d{7}\b')),
    ('APIFY_ID', 'WARN', re.compile(r'(?i)(?:dataset(?:Id)?|run\s?id|actor\s+run)\W{0,6}([A-Za-z0-9]{17})\b')),
    ('PRIVATE_IP', 'WARN', re.compile(r'\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b')),
]
EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)')
PHONE = re.compile(r'(?<![\d.])(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]([2-9]\d{2})[\s.\-](\d{4})(?!\d)')
BINARY_GENERIC = {'SECRET', 'PATH', 'LINKEDIN_PROFILE', 'POSTING'}


class Scanner:
    def __init__(self, entries, opts):
        self.entries = [(c, t, term_regex(t)) for c, t in entries if term_regex(t)]
        self.opts = opts
        self.findings = {}
        self.files = 0
        self.authors = OK_AUTHORS | {a.lower() for a in opts.get('allow_author', [])}
        self.domains = OK_EMAIL_DOMAINS | {d.lower() for d in opts.get('allow_email_domain', [])}

    def add(self, sev, cat, where, line, matched):
        if where.endswith(' [text]'):      # same hit already reported against the raw part
            base = where[:-7]
            if any(k[0] == cat and k[1] == base and k[3] == matched.lower() for k in self.findings):
                return
        key = (cat, where, line, matched.lower())
        self.findings.setdefault(key, (sev, cat, where, line, matched))

    # -- text
    def scan_text(self, text, where, binary=False, generic=True):
        text = text.translate(ZW)
        if not text:
            return
        for cat, term, rx in self.entries:
            for m in rx.finditer(text):
                self.add('WARN' if cat in WARN_CATS else 'FAIL', cat, where, text.count('\n', 0, m.start()) + 1, m.group(0))
        if not generic:
            return
        for cat, sev, rx in GENERIC:
            if binary and cat not in BINARY_GENERIC:
                continue
            for m in rx.finditer(text):
                val = m.group(0)
                if cat == 'PATH' and m.groups() and PLACEHOLDER.search(m.group(1) or ''):
                    continue
                if cat in ('SECRET', 'LINKEDIN_PROFILE') and PLACEHOLDER.search(val):
                    continue
                if cat == 'POSTING' and re.search(r'(?<!\d)0{4,}\d+', val):      # sample links use ids that start 0000: obviously fictional
                    continue
                self.add(sev, cat, where, text.count('\n', 0, m.start()) + 1, val)
        for m in EMAIL.finditer(text):
            dom = m.group(1).lower()
            if dom in self.domains or m.group(0).lower() in OK_EMAILS or PLACEHOLDER.search(m.group(0)):
                continue
            self.add('FAIL', 'EMAIL', where, text.count('\n', 0, m.start()) + 1, m.group(0))
        if not binary:
            for m in PHONE.finditer(text):
                if m.group(2) == '555' and m.group(3).startswith('01'):
                    continue
                self.add('FAIL', 'PHONE', where, text.count('\n', 0, m.start()) + 1, m.group(0))

    def scan_name(self, name, where):
        self.scan_text(name, where + ' [file name]', generic=False)
        base = os.path.basename(name)
        low = base.lower()
        ext = os.path.splitext(low)[1]
        if base in JUNK_NAMES or low.endswith(JUNK_EXT) or base.startswith('~$'):
            self.add('WARN', 'JUNK', where, 0, base)
        if low in RISKY_NAMES or low.startswith('id_rsa') or ext in RISKY_EXT:
            self.add('FAIL', 'RISKY_FILE', where, 0, base)

    # -- bytes
    def scan_bytes(self, data, where, name, depth=0):
        ext = os.path.splitext(name.lower())[1]
        if ext in ARCHIVES or data[:4] == b'PK\x03\x04':
            if self.scan_archive(data, where, depth):
                return
        if ext in REVIEW:
            self.add('WARN', 'REVIEW', where, 0, 'binary file: open and check by eye')
            self.scan_text(data.decode('latin-1'), where, binary=True)
            self.scan_text(data.decode('utf-16-le', 'ignore'), where, binary=True, generic=False)
            self.binary_meta(data, where, ext)
            return
        if b'\x00' in data[:4096] and not data.startswith((b'\xff\xfe', b'\xfe\xff')):
            self.add('WARN', 'REVIEW', where, 0, 'unrecognised binary: open and check by eye')
            self.scan_text(data.decode('latin-1'), where, binary=True)
            self.scan_text(data.decode('utf-16-le', 'ignore'), where, binary=True, generic=False)
            return
        for enc in ('utf-8', 'utf-16', 'latin-1'):
            try:
                text = data.decode(enc); break
            except (UnicodeDecodeError, UnicodeError):
                continue
        self.scan_text(text, where)
        if ext in ('.xml', '.rels', '.html', '.htm', '.svg') or text.lstrip().startswith('<'):
            plain = self.strip_xml(text)
            if plain != text:
                self.scan_text(plain, where + ' [text]', generic=False)

    @staticmethod
    def strip_xml(xml):
        xml = re.sub(r'</(?:w:p|a:p|si|text:p|p|div|li|tr)>|<(?:w:br|w:tab|br)\s*/?>', '\n', xml)
        return re.sub(r'<[^>]+>', '', xml)

    def binary_meta(self, data, where, ext):
        if ext == '.pdf':
            for m in re.finditer(rb'/Author\s*\((.*?)\)', data):
                v = m.group(1).decode('latin-1', 'ignore').strip()
                if v and v.lower() not in self.authors:
                    self.add('FAIL', 'META', where, 0, 'PDF Author: ' + v)
        if ext == '.png':
            pos = 8
            while pos + 8 <= len(data):
                ln, typ = struct.unpack('>I4s', data[pos:pos + 8])
                if typ in (b'tEXt', b'iTXt', b'zTXt'):
                    key = data[pos + 8:pos + 8 + ln].split(b'\x00')[0].decode('latin-1', 'ignore')
                    if key.lower() in ('author', 'copyright', 'creator', 'comment', 'location', 'source'):
                        self.add('WARN', 'META', where, 0, 'PNG text chunk: ' + key)
                pos += 12 + ln
        if ext in ('.jpg', '.jpeg', '.heic', '.tif', '.tiff') and b'Exif\x00\x00' in data[:65536]:
            self.add('WARN', 'META', where, 0, 'EXIF block present (strip it: exiftool -all=)')
        if b'<x:xmpmeta' in data:
            self.add('WARN', 'META', where, 0, 'XMP metadata packet present')

    # -- archives
    def scan_archive(self, data, where, depth):
        if depth > 3:
            self.add('WARN', 'REVIEW', where, 0, 'archive nested too deep to inspect')
            return True
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            return False
        infos = z.infolist()
        if len(infos) > 5000 or sum(i.file_size for i in infos) > 300 * 1024 * 1024:
            self.add('WARN', 'REVIEW', where, 0, 'archive too large to inspect')
            return True
        for i in infos:
            if i.is_dir():
                continue
            inner = where + '!' + i.filename
            self.scan_name(i.filename, inner)
            try:
                blob = z.read(i)
            except Exception as e:  # encrypted or corrupt
                self.add('WARN', 'REVIEW', inner, 0, 'cannot read entry: %s' % e); continue
            low = i.filename.lower()
            if low.endswith(('docprops/core.xml', 'docprops/app.xml', 'docprops/custom.xml', 'meta.xml')):
                self.ooxml_meta(blob.decode('utf-8', 'ignore'), inner)
            self.scan_bytes(blob, inner, i.filename, depth + 1)
        return True

    def ooxml_meta(self, xml, where):
        for m in re.finditer(r'<((?:dc:creator|cp:lastModifiedBy|dc:lastModifiedBy|meta:initial-creator|Company|Manager|dc:contributor|meta:user-defined)[^>]*)>([^<]*)<', xml):
            v = m.group(2).strip()
            if v and v.lower() not in self.authors:
                self.add('FAIL', 'META', where, 0, '%s = %s' % (m.group(1).split()[0], v))
        for m in re.finditer(r'<vt:lpwstr>([^<]+)</vt:lpwstr>', xml):
            self.add('WARN', 'META', where, 0, 'custom property: ' + m.group(1)[:60])

    # -- tree
    def scan_tree(self, root):
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for d in dirs:
                self.scan_name(os.path.relpath(os.path.join(dirpath, d), root), os.path.relpath(os.path.join(dirpath, d), root) + '/')
            for fn in sorted(files):
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                self.files += 1
                self.scan_name(rel, rel)
                if os.path.islink(p):
                    self.add('FAIL', 'SYMLINK', rel, 0, 'symbolic link (may point outside the repo)'); continue
                size = os.path.getsize(p)
                if size > 20 * 1024 * 1024:
                    self.add('WARN', 'REVIEW', rel, 0, 'file over 20 MB not scanned'); continue
                if size > 5 * 1024 * 1024:
                    self.add('WARN', 'BIGFILE', rel, 0, '%.1f MB' % (size / 1048576.0))
                with open(p, 'rb') as f:
                    self.scan_bytes(f.read(), rel, fn)
        self.scan_git(root)

    def git(self, root, *args):
        try:
            r = subprocess.run(['git', '-C', root] + list(args), capture_output=True, text=True, timeout=60)
            return r.stdout if r.returncode == 0 else ''
        except Exception:
            return ''

    def scan_git(self, root):
        if not os.path.isdir(os.path.join(root, '.git')):
            return
        cfg = os.path.join(root, '.git', 'config')
        if os.path.exists(cfg):
            text = open(cfg, encoding='utf-8', errors='ignore').read()
            self.scan_text(text, '.git/config')
            if re.search(r'https?://[^/\s:@]+:[^/\s@]+@', text):
                self.add('FAIL', 'SECRET', '.git/config', 0, 'credentials inside a remote URL')
        for line in self.git(root, 'log', '--all', '--format=%an%x09%ae%x09%cn%x09%ce').splitlines():
            for field in line.split('\t'):
                if '@' in field:
                    dom = field.split('@')[-1].lower()
                    if dom not in self.domains and field.lower() not in OK_EMAILS:
                        self.add('FAIL', 'GIT_AUTHOR', 'git history', 0, field)
                elif field.strip():
                    self.scan_text(field, 'git history [author name]', generic=False)
        self.scan_text(self.git(root, 'log', '--all', '--format=%s%n%b'), 'git history [messages]')
        self.scan_text(self.git(root, 'for-each-ref', '--format=%(refname)'), 'git refs', generic=False)
        for line in self.git(root, 'log', '--all', '--name-only', '--format=').splitlines():
            if line.strip():
                self.scan_text(line, 'git history [file name: %s]' % line.strip(), generic=False)

    def result(self):
        order = {'FAIL': 0, 'WARN': 1}
        return sorted(self.findings.values(), key=lambda f: (order[f[0]], f[1], f[2], f[3]))


# ------------------------------------------------------------------ commands
def cmd_scan(a):
    root = os.path.abspath(a.path)
    if not os.path.isdir(root):
        print('not a directory: ' + a.path, file=sys.stderr); return 2
    entries = []
    if a.denylist:
        d = os.path.abspath(a.denylist)
        if not os.path.exists(d):
            print('denylist not found: ' + a.denylist, file=sys.stderr); return 2
        if d == root or d.startswith(root + os.sep):
            print('REFUSED: the denylist is inside the folder being scanned. Move it outside the repo.', file=sys.stderr); return 2
        entries = parse_denylist(d)
    elif not a.generic_only:
        print('No --denylist given. Pass one, or use --generic-only to run the built-in checks only.', file=sys.stderr); return 2
    sc = Scanner(entries, dict(allow_author=a.allow_author or [], allow_email_domain=a.allow_email_domain or []))
    sc.scan_tree(root)
    res = sc.result()
    fails = [f for f in res if f[0] == 'FAIL']
    warns = [f for f in res if f[0] == 'WARN']
    lines = ['Privacy scan of %s' % root,
             '%d files, %d denylist entries%s' % (sc.files, len(entries), '' if entries else ' (generic checks only)'),
             'FAIL %d | WARN %d' % (len(fails), len(warns)), '']
    for sev, cat, where, line, matched in res:
        lines.append('%s %-16s %s%s  %s' % (sev, cat, where, (':%d' % line) if line else '', mask(matched, a.show) if cat not in ('REVIEW', 'JUNK', 'BIGFILE') else matched))
    out = '\n'.join(lines)
    print(out)
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
    bad = fails or (a.strict and warns)
    print('\nRESULT: %s' % ('NOT SAFE TO PUBLISH' if bad else ('clean (review the WARN lines by eye)' if warns else 'clean')))
    return 1 if bad else 0


def cmd_manifest(a):
    root = os.path.abspath(a.path)
    rows = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            rows.append((os.path.relpath(p, root).replace(os.sep, '/'), os.path.getsize(p), h))
    text = '\n'.join('%s  %9d  %s' % (h, s, p) for p, s, h in rows) + '\n'
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text)
    print('%d files, %d bytes' % (len(rows), sum(r[1] for r in rows)))
    if a.compare:
        old = {}
        for ln in open(a.compare, encoding='utf-8'):
            parts = ln.split(None, 2)
            if len(parts) == 3:
                old[parts[2].strip()] = parts[0]
        new = {p: h for p, s, h in rows}
        for p in sorted(set(new) - set(old)): print('ADDED   ', p)
        for p in sorted(set(old) - set(new)): print('REMOVED ', p)
        for p in sorted(p for p in new if p in old and new[p] != old[p]): print('CHANGED ', p)
    elif not a.out:
        for p, s, h in rows: print('%9d  %s' % (s, p))
    return 0


def read_any(path):
    ext = os.path.splitext(path.lower())[1]
    if ext in OOXML:
        z = zipfile.ZipFile(path); out = []
        for n in z.namelist():
            if n.endswith('.xml') and (n.startswith(('word/', 'xl/sharedStrings', 'ppt/slides/')) or n.endswith('document.xml')):
                out.append(Scanner.strip_xml(z.read(n).decode('utf-8', 'ignore')))
        return '\n'.join(out)
    if ext == '.pdf':
        if shutil.which('pdftotext'):
            return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout
        print('note: pdftotext not found, skipping ' + path, file=sys.stderr); return ''
    return open(path, encoding='utf-8', errors='ignore').read()


def walk_json(o, key=''):
    if isinstance(o, dict):
        for k, v in o.items():
            for x in walk_json(v, str(k)): yield x
    elif isinstance(o, list):
        for v in o:
            for x in walk_json(v, key): yield x
    elif isinstance(o, (str, int)) and o is not None:
        yield key, str(o)


def cmd_build(a):
    ent = {}
    def add(cat, term):
        term = term.strip()
        if len(term) >= 3:
            ent.setdefault((cat.upper(), term.lower()), term)
    exceptions = set()
    if a.seed:
        for ln in open(a.seed, encoding='utf-8'):
            ln = ln.strip()
            if ln.startswith('!'): exceptions.add(ln[1:].strip().lower())
            elif '|' in ln and not ln.startswith('#'):
                c, t = ln.split('|', 1); add(c, t)
    for p in a.tracker or []:
        for key, val in walk_json(json.load(open(p, encoding='utf-8'))):
            k = key.lower()
            if k in ('company', 'employer', 'organization') or any(s in k for s in ('agency', 'staffing')):
                add('COMPANY', val); add('COMPANY', re.sub(r'\s*\(.*?\)', '', val))
            elif k in ('req_id', 'source_job_id', 'job_id', 'linkedin_job_id', 'requisition', 'folder'):
                add('ID', val)
            elif k == 'jd_file':
                add('ID', os.path.splitext(os.path.basename(val))[0])
            elif any(s in k for s in ('recruiter', 'interviewer', 'hiring_manager', 'contact', 'panel')):
                if '@' in val: add('EMAIL', val)
                elif re.fullmatch(r"[A-Za-z][A-Za-z.'\-]+(?: [A-Za-z][A-Za-z.'\-]+){1,3}", val): add('PERSON', val)
    for p in (a.resume or []) + (a.source or []):
        text = read_any(p)
        for m in re.finditer(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+', text): add('EMAIL', m.group(0))
        for m in PHONE.finditer(text): add('PHONE', m.group(0))
        for m in re.finditer(r'(?:linkedin\.com/in|github\.com)/[A-Za-z0-9_\-]+', text, re.I): add('HANDLE', m.group(0))
    for p in a.resume or []:
        first = next((l.strip() for l in read_any(p).splitlines() if l.strip()), '')
        toks = re.findall(r"[A-Za-z][A-Za-z'\-]+", first)
        if 2 <= len(toks) <= 4 and len(first) < 50:
            add('NAME', ' '.join(toks))
            add('NAME', toks[0][0] + toks[-1])          # e.g. "JDoe" style file prefixes
            add('NAME', toks[-1] + ', ' + toks[0])
            print('Name read from the top of %s: confirm it is right, and add nicknames to the seed file.' % os.path.basename(p))
    for p in a.metrics or []:
        text = read_any(p)
        pats = [r'\$\s?\d[\d,]*(?:\.\d+)?\s?(?:K|M|B|k|million|billion|thousand)\b', r'\b\d{1,4}(?:\.\d+)?\s?%',
                r'\b\d+\+?\s+(?:[A-Za-z\-]+\s+){0,2}(?:engineers|customers|accounts|programs|products|wins|people|members|countries|sites|vendors|suppliers|teams|projects)\b']
        for pt in pats:
            for m in re.finditer(pt, text): add('METRIC', m.group(0))
    final = sorted(((c, t) for (c, k), t in ent.items() if k not in exceptions), key=lambda x: (x[0], x[1].lower()))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('# PRIVATE DENYLIST. Never commit this file. Keep it outside the repo folder.\n# Format: CATEGORY|term   (!term = exception)\n')
        for ex in sorted(exceptions): f.write('!%s\n' % ex)
        for c, t in final: f.write('%s|%s\n' % (c, t))
    from collections import Counter
    cnt = Counter(c for c, t in final)
    print('Wrote %d entries to %s' % (len(final), a.out))
    print(', '.join('%s %d' % kv for kv in sorted(cnt.items())))
    return 0


# ------------------------------------------------------------------ selftest
def _docx(path, paragraphs, creator='', runs_split=None):
    body = ''.join('<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % p for p in paragraphs)
    if runs_split:
        a, b = runs_split
        body += '<w:p><w:r><w:t>%s</w:t></w:r><w:r><w:t>%s</w:t></w:r></w:p>' % (a, b)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/document.xml', '<w:document><w:body>%s</w:body></w:document>' % body)
        z.writestr('docProps/core.xml', '<cp:coreProperties><dc:creator>%s</dc:creator><cp:lastModifiedBy>%s</cp:lastModifiedBy></cp:coreProperties>' % (creator, creator))


def cmd_selftest(a):
    tmp = tempfile.mkdtemp(prefix='privscan_')
    ok = True
    def check(label, cond):
        nonlocal ok
        print(('PASS  ' if cond else 'FAIL  ') + label); ok = ok and cond
    try:
        REQ = 'JR' + '9998877'
        deny = os.path.join(tmp, 'deny.txt')
        open(deny, 'w').write('NAME|Jordan Quill\nEMPLOYER|Zyxwell Corp\nCOMPANY|Fabrikam Dynamics\nID|%s\nMETRIC|$250%s\nPERSON|Marlo Tessing\nOTHER|Quillsoft\n!Quillsoft\n' % (REQ, 'K'))
        clean, leaky = os.path.join(tmp, 'clean'), os.path.join(tmp, 'leaky')
        os.makedirs(os.path.join(clean, 'docs')); os.makedirs(os.path.join(leaky, 'docs')); os.makedirs(os.path.join(leaky, 'nested'))
        open(os.path.join(clean, 'README.md'), 'w').write('# Demo\nContact: you@example.com\nPath: C:\\Users\\<you>\\Documents\nCandidate: Alex Rivera at Contoso Ltd. Quillsoft is an allowed exception.\n')
        _docx(os.path.join(clean, 'docs', 'sample.docx'), ['Alex Rivera resume', 'Led 12 engineers at Contoso'], creator='ai-jobsearch')
        # fixtures are assembled from pieces so this source file contains no literal leak patterns
        EM, PH = 'jordan.quill' + '@' + 'gmail.com', '(310) 555' + '-2368'
        TOK = 'apify_' + 'api_' + 'a1B2c3D4e5F6g7H8i9J0'
        PTH = 'C:' + '\\Users\\jq' + 'uill\\Documents\\x'
        POST = 'https://www.linkedin.com/' + 'jobs/view/senior-tpm-at-fabrikam-4471234567'
        PROF = 'https://www.linkedin.com/' + 'in/jordan-quill-123'
        IP = '192.168' + '.40.8'
        open(os.path.join(leaky, 'README.md'), 'w').write('Owner: Jordan Quill\nMail: %s\nCall %s\nAPIFY=%s\nsee %s\n%s\n%s\nreq %s and salary %s\nhost %s\n' % (EM, PH, TOK, PTH, POST, PROF, REQ, '$250' + 'K', IP))
        open(os.path.join(leaky, 'Jordan_Quill_resume.md'), 'w').write('x\n')
        open(os.path.join(leaky, '.env'), 'w').write('A=1\n')
        open(os.path.join(leaky, 'zero.txt'), 'w', encoding='utf-8').write('Zyx\u200bwell Corp\n')
        _docx(os.path.join(leaky, 'docs', 'resume.docx'), ['Worked at Fabrikam Dynamics'], creator='Jordan Q.', runs_split=('Zyx', 'well Corp'))
        inner = os.path.join(tmp, 'inner.docx'); _docx(inner, ['Marlo Tessing referred me'])
        with zipfile.ZipFile(os.path.join(leaky, 'nested', 'bundle.plugin'), 'w') as z:
            z.write(inner, 'skills/x/inner.docx')
        png = b'\x89PNG\r\n\x1a\n' + struct.pack('>I4s', 12, b'tEXt') + b'Author\x00Jordan' + b'\x00\x00\x00\x00'
        open(os.path.join(leaky, 'docs', 'logo.png'), 'wb').write(png)
        if shutil.which('git'):
            subprocess.run(['git', 'init', '-q', leaky]); subprocess.run(['git', '-C', leaky, 'add', '-A'])
            subprocess.run(['git', '-C', leaky, '-c', 'user.name=Jordan Quill', '-c', 'user.email=jordan@' + 'gmail.com', 'commit', '-q', '-m', 'init'], capture_output=True)
        ns = argparse.Namespace(denylist=deny, report=None, strict=False, show=True, generic_only=False, allow_author=[], allow_email_domain=[], path=clean)
        sc = Scanner(parse_denylist(deny), {}); sc.scan_tree(clean)
        check('clean tree has no FAIL findings (examples, placeholders, exception honoured)', not [f for f in sc.result() if f[0] == 'FAIL'])
        sc = Scanner(parse_denylist(deny), {}); sc.scan_tree(leaky)
        got = {(f[1], f[2]) for f in sc.result()}
        text = ' '.join(('%s|%s|%s' % (f[1], f[2], f[4])).lower() for f in sc.result())
        expect = [('NAME in a text file', 'name|readme.md|jordan quill'), ('email', 'email|readme.md|' + EM),
                  ('phone', 'phone|readme.md'), ('API token', 'secret|readme.md'), ('personal folder path', 'path|readme.md'),
                  ('real posting link', 'posting|readme.md'), ('LinkedIn profile', 'linkedin_profile|readme.md'),
                  ('requisition ID', 'id|readme.md|' + REQ.lower()), ('metric (WARN)', 'metric|readme.md'), ('private IP (WARN)', 'private_ip|readme.md'),
                  ('name in a file name', 'name|jordan_quill_resume.md [file name]'), ('.env file', 'risky_file|.env'),
                  ('zero-width obfuscation', 'employer|zero.txt'), ('term split across docx runs', 'employer|docs/resume.docx!word/document.xml'),
                  ('company inside docx', 'company|docs/resume.docx!word/document.xml'), ('docx author metadata', 'meta|docs/resume.docx!docprops/core.xml'),
                  ('person inside nested plugin>docx', 'person|nested/bundle.plugin!skills/x/inner.docx!word/document.xml'),
                  ('PNG text chunk', 'meta|docs/logo.png'), ('image listed for review', 'review|docs/logo.png')]
        if shutil.which('git'):
            expect += [('git author email', 'git_author|git history')]
        for label, needle in expect:
            check('catches ' + label, needle in text)
        check('exit code 1 on findings', cmd_scan(argparse.Namespace(denylist=deny, report=None, strict=False, show=False, generic_only=False, allow_author=[], allow_email_domain=[], path=leaky)) == 1)
        shutil.copy(deny, os.path.join(clean, 'deny.txt'))
        check('refuses a denylist inside the scanned folder', cmd_scan(argparse.Namespace(denylist=os.path.join(clean, 'deny.txt'), report=None, strict=False, show=False, generic_only=False, allow_author=[], allow_email_domain=[], path=clean)) == 2)
        os.remove(os.path.join(clean, 'deny.txt'))
        check('exit code 0 on the clean tree', cmd_scan(argparse.Namespace(denylist=deny, report=None, strict=False, show=False, generic_only=False, allow_author=[], allow_email_domain=[], path=clean)) == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nSELFTEST ' + ('PASSED' if ok else 'FAILED'))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('scan'); q.add_argument('path'); q.add_argument('--denylist'); q.add_argument('--generic-only', action='store_true')
    q.add_argument('--report'); q.add_argument('--strict', action='store_true'); q.add_argument('--show', action='store_true', help='print matched text instead of masking it')
    q.add_argument('--allow-author', action='append'); q.add_argument('--allow-email-domain', action='append')
    q = sub.add_parser('manifest'); q.add_argument('path'); q.add_argument('--out'); q.add_argument('--compare')
    q = sub.add_parser('build-denylist'); q.add_argument('--out', required=True); q.add_argument('--seed')
    q.add_argument('--tracker', action='append'); q.add_argument('--resume', action='append'); q.add_argument('--metrics', action='append'); q.add_argument('--source', action='append')
    sub.add_parser('selftest')
    a = p.parse_args()
    sys.exit({'scan': cmd_scan, 'manifest': cmd_manifest, 'build-denylist': cmd_build, 'selftest': cmd_selftest}[a.cmd](a))


if __name__ == '__main__':
    main()
