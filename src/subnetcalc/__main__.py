"""Allow ``python -m subnetcalc`` to run the CLI."""

from subnetcalc.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
