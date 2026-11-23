"""Module entrypoint for 'python -m pcb_insight'."""

import sys
from pcb_insight.plugin_entry import main

if __name__ == "__main__":
    sys.exit(main())
