import datetime as dt
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(ROOT)


def load():
    with open(os.path.join(ROOT, "config", "generation.yml")) as f:
        cfg = yaml.safe_load(f)
    cfg["scenario_dates"] = {k: _d(v) for k, v in cfg["scenario_dates"].items()}
    cfg["history_start"] = _d(cfg["history_start"])
    return cfg


def _d(v):
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def out_dir(*parts):
    p = os.path.join(ROOT, "output", *parts)
    os.makedirs(p, exist_ok=True)
    return p


def evidence_dir(*parts):
    p = os.path.join(PROJECT, "docs", "dissertation_evidence", *parts)
    os.makedirs(p, exist_ok=True)
    return p
