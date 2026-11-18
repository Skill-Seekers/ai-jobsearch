"""One command line for the whole suite:  python -m jobsearch <command> ...   (or  python path/to/ai-jobsearch/jobsearch <command>)

Exit codes: 0 done, 1 finished but found a problem to act on (config errors, refused change, a warning gate), 2 could not run
(bad arguments, missing file, no config). Python 3.8+, standard library only."""
import argparse, json, os, sys
from datetime import date
from jobsearch import __version__, ats, config, dashboard, extract, gaps, liveness, queries, score, seen, tracker
from jobsearch.util import load_rows, write_json, read_text


def today():
    return date.today().isoformat()


def out(*lines):
    for l in lines:
        print(l)


def cmd_check(c, a):
    errs, warn = config.validate(c)
    out(config.show(c))
    for w in warn:
        out('WARN  ' + w)
    for e in errs:
        out('ERROR ' + e)
    out('config ok' if not errs else '%d error(s)' % len(errs))
    return 1 if errs else 0


def cmd_queries(c, a):
    if a.mark:
        queries.mark(c, a.mark, a.status, a.date or today())
        out('marked %s %s' % (a.mark, a.status))
        return 0
    if a.plan:
        for s in queries.plan(c):
            out('Stage %d: %s' % (s['stage'], ', '.join(s['items'])))
        return 0
    out(queries.render(c, a.source, a.batch, a.pending))
    return 0


def cmd_extract(c, a):
    if not os.path.isdir(a.raw):
        raise FileNotFoundError('raw folder not found: %s (save each source\'s rows as .json files there)' % a.raw)
    r = extract.run(c, a.raw, a.date or today(), a.out)
    out('raw %d -> unique %d -> in window (since %s) %d -> kept %d, dropped %d' % (r['raw'], r['unique'], r['cut'], r['in_window'], r['kept'], r['dropped']),
        'dropped by: ' + (', '.join('%s %d' % kv for kv in sorted(r['buckets'].items())) or 'nothing'),
        'wrote %s and %s' % (os.path.join(a.out, 'keep.json'), os.path.join(a.out, 'dropped.json')))
    return 0


def cmd_score(c, a):
    r = score.run(c, a.file, a.date or today(), a.out)
    out('scored %d rows -> %s' % (r['n'], r['out']), 'buckets: ' + ', '.join('%s %d' % kv for kv in sorted(r['buckets'].items())),
        'score spread: ' + ', '.join('%d-%d: %d' % (k, k + 9, v) for k, v in r['dist'].items()),
        'scope gate moved %d role(s) out of the main buckets' % r['scope_out'])
    if r['saturated']:
        out('WARN  %d roles share the top score %d: the keyword scorer is saturating. Review the top of the list by hand.' % (r['tied'], r['top']))
    return 0


def cmd_adjust(c, a):
    r = score.adjust(c, a.file, a.adjustments, a.out)
    out('applied %d adjustment(s) -> %s' % (r['applied'], r['out']))
    for m in r['missed']:
        out('WARN  no row matched: %s' % json.dumps(m))
    return 1 if r['missed'] else 0


def cmd_liveness(c, a):
    if a.held:
        lines, rerun, manual = liveness.held_report(c)
        out(*lines)
        return 0
    keep, dropped = liveness.check(c, a.file, a.date or today(), a.out)
    out('open %d | dropped as closed or past deadline %d' % (len(keep), len(dropped)))
    for d in dropped:
        out('  - %s | %s: %s' % (d['company'], d['title'], d['live_note']))
    return 0


def cmd_seen(c, a):
    s = a.action
    if s == 'annotate':
        n, tot = seen.annotate(c, a.file)
        out('%d of %d rows are first-time sightings' % (n, tot))
    elif s == 'ingest':
        r = seen.ingest(c, a.file, a.run, a.date or today(), a.filtered)
        out('ingested %(rows)d rows: %(new)d new, %(seen)d seen before, %(repost)d reposts; store now holds %(total)d postings' % r)
    elif s == 'report':
        out(*seen.report(c, a.run, a.final))
    elif s in ('hold', 'unhold'):
        out(*seen.hold(c, a.ids, s == 'hold', a.date))
    elif s == 'held':
        out(*liveness.held_report(c)[0])
    elif s == 'stats':
        out(seen.stats(c))
    return 0


def cmd_dashboard(c, a):
    r = dashboard.build(c, a.scored, a.dropped or [], run=a.run, day=a.date, sources=a.sources, unavailable=a.unavailable,
                        mode='quick' if a.quick else 'full', notes=a.notes or '', csv_out=True if a.csv else None, out_dir=a.out)
    out('Run #%d: %d results, %d filtered' % (r['run'], r['results'], r['filtered']), 'wrote ' + r['html'])
    if r.get('csv'):
        out('wrote ' + r['csv'])
    return 0


def cmd_tracker(c, a):
    t = a.action
    if t == 'match':
        m = tracker.match(a.company, a.title, tracker.load(c)['applications'], a.link or '', generic=tracker.generic_words(c))
        out(('match: %s (%s, %s)' % (m['id'], m['status'], m.get('outcome') or 'no outcome')) if m else 'no match')
    elif t == 'dupes':
        jd = read_text(a.jd) or ''
        r = tracker.find_dupes(c, jd, a.company or '', a.title or '', a.req_id or '', a.link or '')
        for x in r['tracker']:
            out('tracker: %(id)s [%(status)s] %(company)s - %(title)s :: %(why)s' % {k: x.get(k) for k in ('id', 'status', 'company', 'title', 'why')})
        for x in r['saved_jds']:
            out('saved JD: %(file)s (similarity %(similarity)s)' % x)
        if not (r['tracker'] or r['saved_jds']):
            out('no duplicates found')
        return 1 if (r['tracker'] or r['saved_jds']) else 0
    elif t == 'add':
        e = tracker.add(c, a.company, a.title, a.id, a.req_id or '', a.source_job_id or '', a.jd_file or '', a.folder or '', a.keywords, None, a.note or '')
        out('added %s (status drafted, applied false)' % e['id'])
    elif t == 'update':
        try:
            e = tracker.update(c, a.id, a.status, True if a.applied else None, a.applied_date, a.outcome, a.note, a.confirmed)
        except PermissionError as ex:
            out(str(ex))
            return 1
        out('updated %s: status %s, applied %s' % (e['id'], e['status'], e['applied']))
    elif t == 'report':
        out(*tracker.report(c, a.date))
    return 0


def cmd_ats(c, a):
    text, summ = ats.check(c, a.resume, a.jd)
    out(text)
    if a.md:
        with open(a.md, 'w', encoding='utf-8') as f:
            f.write(text)
        out('saved ' + a.md)
    return 1 if summ['claimed_violations'] else 0


def cmd_gaps(c, a):
    if a.action == 'ingest':
        n, tot = gaps.ingest(c, a.file, a.run, a.min_score)
        out('stored term sets for %d postings (store now %d)' % (n, tot))
        return 0
    lines, _ = gaps.report(c, a.out)
    out(*lines)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog='jobsearch', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--config', help='path to jobsearch.config.json (default: nearest one at or above the current folder; give --config BEFORE the command)')
    p.add_argument('--version', action='version', version='ai-jobsearch ' + __version__)
    sub = p.add_subparsers(dest='cmd', required=True, metavar='command')
    D = 'run date, YYYY-MM-DD (default: today)'
    sub.add_parser('check', help='validate the config and print a summary')
    s = sub.add_parser('queries', help='print the searches to run (LinkedIn URLs, Indeed/Glassdoor/Dice searches)')
    s.add_argument('--source', default='all', choices=['all', 'linkedin', 'indeed', 'glassdoor', 'dice'], help='only this source')
    s.add_argument('--batch', help='only this LinkedIn batch (A for the general queries, B1, B2, ...)')
    s.add_argument('--pending', action='store_true', help='skip batches already marked DONE')
    s.add_argument('--plan', action='store_true', help='print the stage plan instead of the queries')
    s.add_argument('--mark', metavar='LABEL', help='record progress for a batch (with --status and --date)')
    s.add_argument('--status', default='DONE', help='status to record with --mark (default DONE)'); s.add_argument('--date', help=D)
    s = sub.add_parser('extract', help='merge raw rows from every source; de-duplicate; apply window and exclusions')
    s.add_argument('--raw', required=True, help='folder of raw *.json files, one list of rows per file')
    s.add_argument('--out', required=True, help='folder for keep.json and dropped.json'); s.add_argument('--date', help=D)
    s = sub.add_parser('score', help='score and bucket kept roles, apply the scope gate')
    s.add_argument('file', help='keep.json from extract'); s.add_argument('--date', help=D); s.add_argument('--out', help='default: scored.json beside the input')
    s = sub.add_parser('adjust', help='apply recorded manual score adjustments (each needs a reason)')
    s.add_argument('file', help='scored.json'); s.add_argument('adjustments', help='JSON list of adjustments'); s.add_argument('--out', help='default: overwrite FILE')
    s = sub.add_parser('liveness', help='drop postings that say closed or are past an apply-by date; --held lists held roles')
    s.add_argument('file', nargs='?', help='scored.json'); s.add_argument('--date', help=D); s.add_argument('--out', help='folder for scored_live.json and dropped_live.json')
    s.add_argument('--held', action='store_true', help='report held roles and which batches to re-run')
    s = sub.add_parser('seen', help='cross-run memory of every posting seen')
    s.add_argument('action', choices=['annotate', 'ingest', 'report', 'hold', 'unhold', 'held', 'stats'], help='annotate marks first-time sightings in FILE; ingest records a run; report summarises one')
    s.add_argument('file', nargs='?', help='scored_live.json (annotate, ingest)'); s.add_argument('--run', type=int, help='run number'); s.add_argument('--date', help=D)
    s.add_argument('--filtered', help='dropped.json to record alongside (ingest)'); s.add_argument('--final', action='store_true', help='report: final summary')
    s.add_argument('--ids', nargs='*', default=[], help='posting keys such as li:0000000101 (hold, unhold)')
    s = sub.add_parser('dashboard', help='build the HTML dashboard (CSV optional)')
    s.add_argument('scored', help='scored_live.json'); s.add_argument('--dropped', nargs='*', help='dropped.json and dropped_live.json'); s.add_argument('--run', type=int, help='run number (default: count of dashboards + 1)')
    s.add_argument('--date', help=D); s.add_argument('--sources', nargs='*', help='sources that returned rows'); s.add_argument('--unavailable', nargs='*', help='sources unavailable or low-confidence')
    s.add_argument('--quick', action='store_true', help='label the run "Quick run, partial coverage"'); s.add_argument('--notes', help='scoring notes and adjustments, shown in the footer')
    s.add_argument('--csv', action='store_true', help='also write the CSV report (default: off unless outputs.csv is true)'); s.add_argument('--out', help='output folder (default: paths.search)')
    s = sub.add_parser('tracker', help='application tracker')
    s.add_argument('action', choices=['match', 'dupes', 'add', 'update', 'report'], help='match a posting; check for repeats; add a drafted entry; record a confirmed status; summarise')
    s.add_argument('--company'); s.add_argument('--title'); s.add_argument('--link', help='posting URL (match, dupes)'); s.add_argument('--jd', help='saved JD file (dupes)')
    s.add_argument('--req-id', help="employer's requisition id"); s.add_argument('--id', help='tracker entry id'); s.add_argument('--source-job-id', help='job-board posting id from the URL')
    s.add_argument('--jd-file', help='path of the saved JD (add)'); s.add_argument('--folder', help='tailored package folder (add)'); s.add_argument('--keywords', nargs='*', help='discriminating title words (add)')
    s.add_argument('--note'); s.add_argument('--status', help='drafted, applied, screen, interview, offer, declined, closed, passed (update)'); s.add_argument('--applied', action='store_true', help='mark applied (update)')
    s.add_argument('--applied-date', help='YYYY-MM-DD (update)'); s.add_argument('--outcome', help='free text such as closed or declined (update)')
    s.add_argument('--confirmed', action='store_true', help='required for any status change: the candidate must have said so'); s.add_argument('--date', help=D)
    s = sub.add_parser('ats', help='ATS parse-safety and keyword-gap check of a resume .docx against a JD')
    s.add_argument('resume', help='.docx'); s.add_argument('jd', help='saved JD (.txt, .md)'); s.add_argument('--md', help='also save the report here')
    s = sub.add_parser('gaps', help='skill-gap report from saved JDs, or ingest strong-fit scrape terms')
    s.add_argument('action', choices=['report', 'ingest']); s.add_argument('file', nargs='?', help='scored_live.json (ingest)'); s.add_argument('--run', help='run number (ingest)')
    s.add_argument('--min-score', type=int, default=65, help='ingest only roles at or above this score'); s.add_argument('--out', help='report folder (default: paths.search)')
    return p


HANDLERS = dict(check=cmd_check, queries=cmd_queries, extract=cmd_extract, score=cmd_score, adjust=cmd_adjust, liveness=cmd_liveness, seen=cmd_seen,
                dashboard=cmd_dashboard, tracker=cmd_tracker, ats=cmd_ats, gaps=cmd_gaps)

NEEDS = {('tracker', 'match'): ('company', 'title'), ('tracker', 'add'): ('company', 'title'), ('tracker', 'update'): ('id',), ('tracker', 'dupes'): ('jd',),
         ('seen', 'annotate'): ('file',), ('seen', 'ingest'): ('file', 'run'), ('seen', 'hold'): ('ids',), ('seen', 'unhold'): ('ids',), ('gaps', 'ingest'): ('file', 'run')}


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    try:
        for k in NEEDS.get((a.cmd, getattr(a, 'action', None)), ()):
            if not getattr(a, k):
                p.error('%s %s needs --%s' % (a.cmd, a.action, k.replace('_', '-')) if k not in ('file',) else '%s %s needs a FILE' % (a.cmd, a.action))
        if a.cmd == 'liveness' and not a.held and not a.file:
            p.error('liveness needs a FILE (or --held)')
        c = config.load(a.config)
        return HANDLERS[a.cmd](c, a)
    except config.ConfigError as e:
        print('ERROR ' + str(e), file=sys.stderr)
        return 2
    except (FileNotFoundError, KeyError, ValueError) as e:
        print('ERROR %s: %s' % (type(e).__name__, e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
