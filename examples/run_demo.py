#!/usr/bin/env python3
"""Run the whole search pipeline on the fictional sample workspace and open nothing: it just prints each step and the
path of the dashboard it built. No job site is contacted; the input rows are in examples/sample-workspace/search/raw.

  python examples/run_demo.py [DEST]        (default: a new folder under your temp directory)
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import build_sample_workspace as sample           # noqa: E402
from jobsearch import cli                          # noqa: E402


def main(dest=None):
    dest = os.path.abspath(dest or tempfile.mkdtemp(prefix='ai-jobsearch-demo-'))
    ws = os.path.join(dest, 'workspace')
    if os.path.exists(ws):
        sys.exit('refusing to overwrite %s; pass a new folder' % ws)
    shutil.copytree(os.path.join(HERE, 'sample-workspace'), ws)
    sample.build(ws)
    day, run = sample.TODAY, os.path.join(ws, 'search', 'runs', sample.TODAY)
    cfg = os.path.join(ws, 'jobsearch.config.json')
    steps = [['check'],
             ['extract', '--raw', os.path.join(ws, 'search', 'raw', day), '--out', run, '--date', day],
             ['score', os.path.join(run, 'keep.json'), '--date', day],
             ['adjust', os.path.join(run, 'scored.json'), os.path.join(ws, 'search', 'raw', 'adjustments.example.json')],
             ['liveness', os.path.join(run, 'scored.json'), '--date', day],
             ['seen', 'annotate', os.path.join(run, 'scored_live.json')],
             ['dashboard', os.path.join(run, 'scored_live.json'), '--dropped', os.path.join(run, 'dropped.json'), os.path.join(run, 'dropped_live.json'),
              '--date', day, '--sources', 'LinkedIn', 'Indeed', 'Glassdoor', '--notes', 'Demo run on fictional data.', '--csv'],
             ['seen', 'ingest', os.path.join(run, 'scored_live.json'), '--run', '1', '--date', day, '--filtered', os.path.join(run, 'dropped.json')],
             ['seen', 'report', '--run', '1'],
             ['tracker', 'report', '--date', day],
             ['ats', os.path.join(ws, 'resume', 'master', 'ARivera_v1.0.docx'), os.path.join(ws, 'resume', 'job_descriptions', 'contoso_senior-tpm-silicon-bringup.txt')],
             ['gaps', 'report']]
    for st in steps:
        print('\n$ jobsearch ' + ' '.join(os.path.basename(x) if os.path.isabs(x) else x for x in st))
        code = cli.main(['--config', cfg] + st)
        if code not in (0, 1):
            sys.exit('step failed with exit code %s' % code)
    print('\nDone. Open this file in a browser:\n  ' + os.path.join(ws, 'search', 'job_search_%s.html' % day))
    return ws


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
