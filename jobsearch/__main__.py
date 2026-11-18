import os, sys

if __package__ in (None, ''):          # allow:  python path/to/ai-jobsearch/jobsearch <command>
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobsearch.cli import main

if __name__ == '__main__':
    sys.exit(main())
