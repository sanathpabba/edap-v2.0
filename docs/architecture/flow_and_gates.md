# End-to-end flow, DQ gates and owner notifications (design as built, not yet run)

## Flow (file source shown; other sources follow the same gates)
```
Source system storage  ->  LANDING pipeline (Common/landing/file_positions)  ->  BRONZE pipeline (<AssetClass>/bronze/file_positions)  ->  SILVER  ->  GOLD
 (sourcedrop/positions)     01..09                                                01..10                                                    01..10      01..09
                            validate whole file                                    read, add meta properties, write                         map, dedup, lookups
                            copy good file to landing                              DQX rules (row level)                                    DQX rules (row level)
                            register file                                          GATE: halt only if whole batch wrong                     GATE: halt only if whole batch wrong
                            WRONG/MISSING file => HALT + email                     row failures => quarantine, continue, email summary      row failures => quarantine, continue, email summary
                                                                                   WHOLE BATCH wrong => HALT + email                         Gold: sanity checks => email if any failed (never halts)
```

## What halts the pipeline (only whole-file / whole-batch problems)
| Where | Condition | Result |
|---|---|---|
| Landing (files) | expected file for the business date **not received** (when the run asks: `--extra expect_file=true`) | owner emailed (`FILE_NOT_RECEIVED`), run logged `HALTED`, task fails |
| Landing (files) | file **wrong as a whole**: unrecognised name, unreadable, wrong/missing/extra header columns, no header, fewer data rows than `min_data_rows` | file copied to `landing/positions/quarantine` (not to inbound), registered `REJECTED`, owner emailed (`FILE_REJECTED`), task fails |
| Landing (API) | the API never answered after the retries | owner emailed (`SOURCE_NOT_RECEIVED`), task fails |
| Bronze / Silver | the share of rows failing **error-level** rules reaches `max_error_rate` (default 50%, per table via a `gate:` block), or the batch is empty | owner emailed (`DQ_HALT`); Bronze: run logged HALTED; Silver: nothing merged and the watermark is not advanced |

A halted table stops only its own steps; the other tables of the layer still run, and the runner then fails the task so downstream tasks (the next layer) do not start.
Nothing is lost: Bronze keeps the raw rows, and the next run (or an Adhoc rerun after a corrected file) picks them up.

## What does NOT halt (row-level problems)
Failing rows (e.g. the 41 injected defects in the D2 position file = 3.1%) are copied to `quarantine.bronze_invalid` / `silver_invalid` with the failed rules, the clean rows
continue to the next layer, and the owner gets a **WARN** email listing the failed checks, counts and sample rows. Gold sanity-check failures send a WARN email; Gold never halts (it is already built).

## Owner email contents
Subject `[EDAP] HALTED|WARNING: <AssetClass> / <layer> / <table> - <headline>`; body: what happened and whether downstream was started, run id and batch id, counts (rows checked,
failed, failure rate, halt limit), the failed checks as `rule | severity | failed / total`, a few sample failing rows, and ready-to-run queries for the quarantine rows and rule results (HTML + plain text).

## Notifier (custom, `edap_framework/notify/notifier.py`)
- Config: `definitions/governance/notifications.yml` (owners and their emails, SMTP settings, default gate, `notify_on`, fallback recipients). Owner = the `owner` tag of the table/entity/product spec.
- Every notification is recorded in `edap.monitoring.notifications` (kind, severity, recipients, status, body), including when it could not be sent.
  Status values: `SENT`, `NOT_SENT_EMAIL_NOT_CONFIGURED`, `NOT_SENT_NO_RECIPIENT`, `SEND_FAILED: ...`, `SUPPRESSED` (Adhoc runs are quiet unless `--extra notify=true`).
- A failure to send never masks the pipeline outcome. Databricks job `email_notifications.on_failure` (from `job_failure_recipients`) is a safety net for crashes.
- To switch on email: fill the owner emails and `from_address`, and create Key Vault secrets `smtp-host`, `smtp-user`, `smtp-password`.

## Demo cases (source_generators/demo.py)
| Case | Command | Expected |
|---|---|---|
| Good file | `demo.py d0` / `d1` | lands, Bronze, no email |
| Row-level defects | `demo.py d2` (41 bad rows of 1,312) | WARN email, rows quarantined, pipeline continues |
| Corrected resend | `demo.py fix-d2` | earlier quarantine rows closed as superseded, Silver takes the new version |
| Whole file wrong | `demo.py wrong-file` (wrong header) | file rejected, HALT email, Silver/Gold for positions not started |
| File not received | run Common landing with `--extra "expect_file=true date=<day>"` and no file for the previous business day | HALT email `FILE_NOT_RECEIVED` |

## Known limits
- A Silver halt leaves the rows already written to `quarantine.silver_invalid` for that attempt; the rerun will add them again (duplicates in quarantine, not in Silver).
- The error-rate limit (50%) is my reading of "whole file is wrong"; set it per table with `gate: {max_error_rate: ...}`.
- Nothing here has run on Databricks; the 65 offline tests check the decision logic, email content, file checks and halting behaviour.
