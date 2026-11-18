#!/usr/bin/env python3
"""Package the repo as an installable Cowork plugin: dist/ai-jobsearch-<version>.plugin (a zip).

  python tools/build_plugin.py [--out DIR]

Includes the plugin manifest, skills, the jobsearch package, docs, examples, README and LICENSE. Leaves out tests,
the privacy scanner's private files, caches and anything git ignores. Standard library only."""
import argparse, json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = ['.claude-plugin', 'skills', 'jobsearch', 'docs', 'examples', 'README.md', 'LICENSE', 'CHANGELOG.md']
SKIP_DIRS = {'__pycache__', '.git', '_private', 'dist'}
SKIP_SUFFIX = ('.pyc', '.pyo', '.tmp')


def files():
    for item in INCLUDE:
        path = os.path.join(ROOT, item)
        if os.path.isfile(path):
            yield item, path
        elif os.path.isdir(path):
            for dp, dns, fns in os.walk(path):
                dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
                for fn in sorted(fns):
                    if fn.endswith(SKIP_SUFFIX):
                        continue
                    full = os.path.join(dp, fn)
                    yield os.path.relpath(full, ROOT).replace(os.sep, '/'), full


def build(out_dir):
    with open(os.path.join(ROOT, '.claude-plugin', 'plugin.json'), encoding='utf-8') as f:
        meta = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, '%s-%s.plugin' % (meta['name'], meta['version']))
    names = []
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for arc, full in files():
            z.write(full, arc)
            names.append(arc)
    return target, names


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist'))
    a = ap.parse_args()
    t, names = build(a.out)
    print('wrote %s (%d files)' % (t, len(names)))
    missing = [n for n in ('.claude-plugin/plugin.json', 'jobsearch/__main__.py', 'skills/job-search/SKILL.md') if n not in names]
    if missing:
        sys.exit('package is missing: ' + ', '.join(missing))
