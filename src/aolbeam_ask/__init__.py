"""aolbeam-ask: a lightweight, stateless terminal AI CLI.

The console command is ``ask``. See the module docstring in ``ask.py`` for the
full feature set and usage.
"""
from .ask import main

__version__ = "0.1.0"
__all__ = ["main", "__version__"]
