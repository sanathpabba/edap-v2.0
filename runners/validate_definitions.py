"""Check all YAML definitions against each other (offline, no Spark).   python runners/validate_definitions.py   (or: edap-validate)"""
import _bootstrap  # noqa: F401  (sets sys.path)
from edap_framework.core.validator import main

if __name__ == "__main__":
    main()
