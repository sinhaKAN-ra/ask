"""Allow ``python -m aolbeam_ask`` to run the CLI."""
import sys

from .ask import main

if __name__ == "__main__":
    sys.exit(main())
