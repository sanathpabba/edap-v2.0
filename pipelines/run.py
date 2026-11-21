"""Repository entry point for a pipeline run; the logic lives in edap_framework.cli (installed as the console command `edap-run`).

  python pipelines/run.py --asset-class Equities --layer bronze --mode Routine [--item file_positions] [--steps 1-5] [--dry-run]
See `python pipelines/run.py --help`."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("EDAP_PROJECT_ROOT", ROOT)
sys.path.insert(0, ROOT)

from edap_framework.cli import LAYERS, build_params, main, parse_args, pipelines_for  # noqa: E402,F401
from edap_framework.pipeline.common import PipelineHalt  # noqa: E402

if __name__ == "__main__":
    try:
        main()
    except PipelineHalt as halt:
        print("PIPELINE HALTED: %s" % halt, file=sys.stderr)
        sys.exit(2)
