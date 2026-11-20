"""Allow `python -m instagram …` as an alias for the runner."""
from .runner import main

raise SystemExit(main())
