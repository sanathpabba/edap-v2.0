"""Check all YAML definitions against each other (offline, no Spark).   python runners/validate_definitions.py"""
import sys

import _bootstrap  # noqa: F401  (sets sys.path)
from edap_framework.core.validator import validate

if __name__ == "__main__":
    errors, warns = validate()
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("%d error(s), %d warning(s)" % (len(errors), len(warns)))
    sys.exit(1 if errors else 0)
