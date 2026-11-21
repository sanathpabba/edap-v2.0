"""DQ gate: turns the DQ statistics of a batch into a decision.

  PASS  every row passed, nothing to say
  WARN  some rows failed error-level rules (quarantined) or warned: the pipeline CONTINUES with the clean rows, the owner gets a summary
  HALT  the WHOLE batch/file is wrong: the share of failing rows reaches max_error_rate (or the batch is empty): downstream is stopped, the owner is told

Only a whole-file/whole-batch failure halts. Row-level problems never stop the pipeline."""
from edap_framework.core import config


class Decision:
    def __init__(self, status, reasons, stats, error_rate):
        self.status, self.reasons, self.stats, self.error_rate = status, reasons, stats, error_rate

    @property
    def halt(self):
        return self.status == "HALT"

    def __repr__(self):
        return "Decision(%s, %.1f%% failing, %s)" % (self.status, self.error_rate * 100, "; ".join(self.reasons) or "clean")


def gate_settings(spec_gate=None):
    """Per-table `gate:` block over the defaults in definitions/governance/notifications.yml."""
    d = config.load_yaml("definitions/governance/notifications.yml")["defaults"]["gate"]
    return {**d, **(spec_gate or {})}


def evaluate(stats, settings):
    total, failed = stats.get("total", 0), stats.get("failed_rows", 0)
    rate = (failed / total) if total else 0.0
    reasons = []
    if total == 0:
        return Decision("HALT", ["batch contains no rows"], stats, 0.0)
    if rate >= settings["max_error_rate"]:
        reasons.append("%d of %d rows (%.1f%%) failed error-level rules: at or above the %.0f%% limit, so the whole batch is treated as wrong"
                       % (failed, total, rate * 100, settings["max_error_rate"] * 100))
        return Decision("HALT", reasons, stats, rate)
    if failed:
        reasons.append("%d of %d rows (%.1f%%) quarantined; the remaining rows continue downstream" % (failed, total, rate * 100))
    if stats.get("warned"):
        reasons.append("%d rows carry warnings (kept)" % stats["warned"])
    return Decision("WARN" if reasons else "PASS", reasons, stats, rate)
