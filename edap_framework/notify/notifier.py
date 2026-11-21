"""Custom notifier: owner emails for halts and warnings, with the failed checks listed in the email.

event = {kind, severity (HALT|WARN|INFO), pipeline: {asset_class, layer, table, mode}, run_id, batch_id, owner, headline,
         reasons: [str], rules: [{rule, criticality, failed_rows, total_rows}], samples: [{rules, record}], counts: {..}, links: [str]}
Every notification is recorded in edap.monitoring.notifications (sent or not). A failure to send never masks the pipeline outcome."""
import datetime as dt
import html
import smtplib
import uuid
from email.message import EmailMessage

from edap_framework.core import config, spark_utils

TABLE = "%s.monitoring.notifications"
DDL = """CREATE TABLE IF NOT EXISTS {t} (
  notification_id STRING, created_ts TIMESTAMP, kind STRING, severity STRING, asset_class STRING, layer STRING, table_name STRING,
  mode STRING, run_id STRING, batch_id STRING, owner STRING, recipients STRING, subject STRING, status STRING, detail STRING, body_text STRING)"""
SCHEMA = ("notification_id string, created_ts timestamp, kind string, severity string, asset_class string, layer string, table_name string, "
          "mode string, run_id string, batch_id string, owner string, recipients string, subject string, status string, detail string, body_text string")


def load_config():
    return config.load_yaml("definitions/governance/notifications.yml")


def resolve_recipients(owner, cfg):
    mail = ((cfg.get("owners") or {}).get(owner) or {}).get("email") or ""
    to = [mail] if mail else []
    return to or list(cfg.get("fallback_recipients") or [])


def build_message(event, subject_prefix="[EDAP]"):
    """Returns (subject, plain_text, html). Pure function: easy to test."""
    p = event["pipeline"]
    where = "%s / %s / %s" % (p["asset_class"], p["layer"], p["table"])
    label = {"HALT": "HALTED", "WARN": "WARNING", "INFO": "INFO"}.get(event["severity"], event["severity"])
    subject = "%s %s: %s - %s" % (subject_prefix, label, where, event["headline"])
    lines = ["%s" % event["headline"], "", "Pipeline : %s (%s run)" % (where, p["mode"]), "Run id   : %s" % event.get("run_id"),
             "Batch id : %s" % event.get("batch_id"), "Owner    : %s" % event.get("owner"), "Time (UTC): %s" % dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), ""]
    if event["severity"] == "HALT":
        lines += ["WHAT HAPPENED", "Downstream layers were NOT started. The raw data is preserved and will be picked up on the next run or an Adhoc rerun.", ""]
    elif event["severity"] == "WARN":
        lines += ["WHAT HAPPENED", "The pipeline continued with the rows that passed; the failing rows are in quarantine.", ""]
    if event.get("reasons"):
        lines += ["DETAILS"] + ["  - %s" % r for r in event["reasons"]] + [""]
    if event.get("counts"):
        lines += ["COUNTS"] + ["  %-22s %s" % (k, v) for k, v in event["counts"].items()] + [""]
    if event.get("rules"):
        lines += ["FAILED CHECKS (rule | severity | failed rows / total rows)"]
        lines += ["  %s | %s | %s / %s" % (r["rule"], r["criticality"], r["failed_rows"], r["total_rows"]) for r in event["rules"]] + [""]
    if event.get("samples"):
        lines += ["SAMPLE FAILING ROWS"] + ["  [%s] %s" % (", ".join(s["rules"]), s["record"][:300]) for s in event["samples"]] + [""]
    if event.get("links"):
        lines += ["WHERE TO LOOK"] + ["  %s" % l for l in event["links"]] + [""]
    text = "\n".join(lines)
    e = html.escape
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s / %s</td></tr>" % (e(r["rule"]), e(r["criticality"]), r["failed_rows"], r["total_rows"]) for r in event.get("rules", []))
    colour = {"HALT": "#b00020", "WARN": "#b26a00"}.get(event["severity"], "#1a5fb4")
    body = ("<h3 style='color:%s'>%s</h3><p><b>%s</b> (%s run)<br>Run %s &middot; Batch %s &middot; Owner %s</p>" % (colour, e(event["headline"]), e(where), e(p["mode"]), e(str(event.get("run_id"))), e(str(event.get("batch_id"))), e(str(event.get("owner"))))
            + ("<ul>%s</ul>" % "".join("<li>%s</li>" % e(r) for r in event.get("reasons", [])))
            + ("<table border='1' cellpadding='4' cellspacing='0'><tr><th>Rule</th><th>Severity</th><th>Failed / total</th></tr>%s</table>" % rows if rows else "")
            + ("<p>Sample failing rows:</p><pre>%s</pre>" % e("\n".join("[%s] %s" % (", ".join(s["rules"]), s["record"][:300]) for s in event["samples"])) if event.get("samples") else "")
            + ("<p>%s</p>" % "<br>".join(e(l) for l in event.get("links", [])) if event.get("links") else ""))
    return subject, text, body


def _send_smtp(spark, env, cfg, to, subject, text, body_html):
    ch = cfg["channels"]["email"]
    if not ch.get("enabled") or not ch.get("from_address"):
        return "NOT_SENT_EMAIL_NOT_CONFIGURED"
    if not to:
        return "NOT_SENT_NO_RECIPIENT"
    try:
        smtp = ch["smtp"]
        host = spark_utils.secret(spark, env, smtp["host_secret"])
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, ch["from_address"], ", ".join(to)
        msg.set_content(text)
        msg.add_alternative(body_html, subtype="html")
        with smtplib.SMTP(host, smtp.get("port", 587), timeout=30) as s:
            if smtp.get("starttls", True):
                s.starttls()
            s.login(spark_utils.secret(spark, env, smtp["user_secret"]), spark_utils.secret(spark, env, smtp["password_secret"]))
            s.send_message(msg)
        return "SENT"
    except Exception as exc:                                                    # noqa: BLE001  never let alerting break the pipeline
        return "SEND_FAILED: %s" % str(exc)[:200]


def notify(spark, env, event, send=True):
    """Build, (optionally) send and record one notification. Returns the status string."""
    cfg = load_config()
    to = resolve_recipients(event.get("owner"), cfg)
    subject, text, body_html = build_message(event, cfg["channels"]["email"].get("subject_prefix", "[EDAP]"))
    status = _send_smtp(spark, env, cfg, to, subject, text, body_html) if send else "SUPPRESSED"
    if spark is not None:
        p = event["pipeline"]
        t = TABLE % env["catalog"]
        spark.sql(DDL.format(t=t))
        spark.createDataFrame([(uuid.uuid4().hex, dt.datetime.utcnow(), event["kind"], event["severity"], p["asset_class"], p["layer"], p["table"], p["mode"],
                                str(event.get("run_id")), str(event.get("batch_id")), event.get("owner"), ", ".join(to), subject, status,
                                "; ".join(event.get("reasons", []))[:1000], text)], SCHEMA).write.mode("append").saveAsTable(t)
    return status
