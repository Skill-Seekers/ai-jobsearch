import json, os, shutil, sys, tempfile, unittest, io, contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'examples'))
import build_sample_workspace as sample                      # noqa: E402
from jobsearch import cli, config                            # noqa: E402

DAY = sample.TODAY
RUN = 'search/runs/' + DAY


class WorkspaceCase(unittest.TestCase):
    """Each test class gets a fresh copy of the fictional sample workspace in a temp folder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='jobsearch-test-')
        self.ws = os.path.join(self.tmp, 'ws')
        shutil.copytree(os.path.join(ROOT, 'examples', 'sample-workspace'), self.ws)
        sample.build(self.ws)
        self.cfg_path = os.path.join(self.ws, 'jobsearch.config.json')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def dump(self, path, obj):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f)

    def slurp(self, path, enc='utf-8'):
        with open(path, encoding=enc) as f:
            return f.read()

    def cfg(self):
        return config.load(self.cfg_path)

    def p(self, *parts):
        return os.path.join(self.ws, *parts)

    def cli(self, *args):
        """Run the CLI; returns (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(['--config', self.cfg_path] + list(args))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def pipeline(self):
        r = self.p(*RUN.split('/'))
        for args in (['extract', '--raw', self.p('search', 'raw', DAY), '--out', r, '--date', DAY],
                     ['score', os.path.join(r, 'keep.json'), '--date', DAY],
                     ['liveness', os.path.join(r, 'scored.json'), '--date', DAY]):
            code, out, err = self.cli(*args)
            self.assertEqual(code, 0, out + err)
        return r

    def load(self, *parts):
        return json.loads(self.slurp(os.path.join(*parts)))
