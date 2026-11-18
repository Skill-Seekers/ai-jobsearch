# Contributing

## Run the tests

```
cd tests
python -m unittest discover -s . -t .
```

Standard library only; no install. Tests build a fresh copy of the fictional sample workspace per test. A change that alters scores or filters needs a test; a change to a skill needs the same care as code (an approval gate removed is a bug).

## Keep personal data out

Before opening a pull request or publishing a fork:

```
python tools/privacy_scan.py selftest
python tools/privacy_scan.py build-denylist --out ../private/denylist.txt --seed ../private/seed.txt ...   # see docs/BUILD_PROCESS.md
python tools/privacy_scan.py scan . --denylist ../private/denylist.txt
```

Keep the denylist outside the repo. Use only fictional names, employers and numbers in examples (`Alex Rivera`, `Contoso`, `Fabrikam`; posting ids that start `0000`). Do not commit resumes, trackers, search results or job descriptions of real people or postings.

## Style

Plain, direct prose in skills and docs. Skills hold steps that need judgement and approvals; arithmetic belongs in the package. Config keys, not code, carry anything role-specific.
